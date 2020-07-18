# -*- coding: utf-8 -*-
""" Playground documentation.

Module defining Playground Base Class

"""

import os
from abc import ABC
import yaml
import pymunk

from simple_playgrounds.utils.definitions import SPACE_DAMPING, CollisionTypes, SceneElementTypes

# pylint: disable=unused-argument
# pylint: disable=line-too-long


class Playground(ABC):
    """ Playground is a Base Class that manages the physical simulation.

    Playground manages the interactions between Agents and Scene Elements.

    Attributes:
        size: size of the scene (width, length).
        scene_elements: list of SceneElements present in the Playground.
        fields: list of fields producing SceneElements in the Playground.
        agents: list of Agents present in the Playground.
        agent_starting_area: position or PositionAreaSampler,
            Starting position of an agent (single agent).
        done: bool, True if the playground reached termination.

    """

    # pylint: disable=too-many-instance-attributes

    scene_entities = []

    def __init__(self, size):

        # Generate Scene
        self.size = size
        self._width, self._length = self.size

        # Initialization of the pymunk space, modelling all the physics
        self.space = self._initialize_space()

        # Public attributes for entities in the playground
        self.scene_elements = []
        self.fields = []
        self.agents = []

        # Private attributes for managing interactions in playground
        self._disappeared_scene_elements = []
        self._grasped_scene_elements = {}

        # Add entities declared in the scene
        for scene_entity in self.scene_entities:
            self.add_scene_element(scene_entity)

        self.done = False

        self.agent_starting_area = None

        self._handle_collisions()

    @staticmethod
    def parse_configuration(key):
        """ Private method that parses yaml configuration files.

        Args:
            key: (str) name of the playground configuration.

        Returns:
            Dictionary of attributes and default values.

        """

        fname = 'configs/playground_default.yml'

        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, fname), 'r') as yaml_file:
            default_config = yaml.load(yaml_file)

        return default_config[key]

    @staticmethod
    def _initialize_space():
        """ Method to initialize Pymunk empty space for 2D physics.

        Returns: Pymunk Space

        """

        space = pymunk.Space()
        space.gravity = pymunk.Vec2d(0., 0.)
        space.damping = SPACE_DAMPING

        return space

    def update(self, steps):
        """ Update the Playground

        Update all SceneElements, Fields, Timers and Grasps
        Runs the Physics engine for n steps.

        Args:
            steps: Number of steps

        """

        for agent in self.agents:
            agent.pre_step()

        for _ in range(steps):
            self.space.step(1. / steps)

        for elem in self.scene_elements:
            elem.pre_step()
            if elem.follows_waypoints:
                self.space.reindex_shapes_for_body(elem.pm_body)

        self._fields_produce()
        self._check_timers()
        self._release_grasps()

    def reset(self):
        """ Reset the Playground to its initial state.

        """

        # remove entities and filter out entities which are temporary
        for entity in self.scene_elements.copy():
            self._remove_scene_element(entity)

        # reset and replace entities that are not temporary
        for entity in self._disappeared_scene_elements.copy():
            entity.reset()
            self.add_scene_element(entity)

        # reset fields
        for entity in self.fields:
            entity.reset()

        # reset agents
        self._remove_agents()
        for agent in self.agents:
            agent.reset()
            self.add_agent(agent)

        self.done = False

    def add_agent(self, agent):
        """ Add an agent to the playground.

        Args:
            agent: Agent.

        """

        self.agents.append(agent)

        agent.size_playground = self.size

        if agent.initial_position is not None:
            pass

        elif self.agent_starting_area is not None:
            agent.initial_position = self.agent_starting_area

        else:
            agent.initial_position = [self._width / 2, self._length / 2, 0]

        agent.position = agent.initial_position

        for body_part in agent.parts:
            self.space.add(*body_part.pm_elements)

    def add_agent_without_overlapping(self, agent, tries=100):
        """ Method to add am Agent to the Playground without overlapping.

        Useful when an Agent has a random initial position, to avoid overlapping.

        Args:
            agent: Agent to add to the Playground
            tries: Number of times the Playground will try to place the new_entity

        """

        trial = 0
        visible_collide_parts = True
        interactive_collide_parts = True

        all_shapes = self.space.shapes.copy()

        while (interactive_collide_parts or visible_collide_parts) and trial < tries:

            self.add_agent(agent)

            visible_collide_parts = False
            interactive_collide_parts = False

            for part in agent.parts:

                visible_collide = False
                interactive_collide = False

                if part.pm_visible_shape is not None:
                    collisions = [part.pm_visible_shape.shapes_collide(shape) for shape in all_shapes]
                    visible_collide = any([len(collision.points) != 0 for collision in collisions])

                if part.pm_interaction_shape is not None:
                    collisions = [part.pm_interaction_shape.shapes_collide(shape) for shape in all_shapes]
                    interactive_collide = any([len(collision.points) != 0 for collision in collisions])

                visible_collide_parts = visible_collide or visible_collide_parts
                interactive_collide_parts = interactive_collide or interactive_collide_parts

            if visible_collide_parts or interactive_collide_parts:
                self.remove_agent(agent)

            trial += 1

        return not (interactive_collide_parts or visible_collide_parts)

    def add_scene_element(self, new_scene_element, new_position=True):
        """ Method to add a SceneElement to the Playground

        Args:
            new_scene_element: Scene Element to add to the Playground
            new_position: If False, will not place the element in a new position.
                Useful when entities are replaced by another.

        """

        new_scene_element.size_playground = self.size

        if new_scene_element.entity_type is SceneElementTypes.FIELD:
            self.fields.append(new_scene_element)

        else:
            if new_position:
                new_scene_element.position = new_scene_element.initial_position

            self.space.add(*new_scene_element.pm_elements)
            self.scene_elements.append(new_scene_element)
            if new_scene_element in self._disappeared_scene_elements:
                self._disappeared_scene_elements.remove(new_scene_element)

    def add_scene_element_without_overlapping(self, scene_element, tries=100):
        """ Method to add a SceneElement to the Playground without overlapping

        Useful when a SceneElement has a random initial position, to avoid overlapping.

        Args:
            scene_element: Scene Element to add to the Playground
            tries: Number of times the Playground will try to place the new_entity

        """

        scene_element.size_playground = self.size

        trial = 0
        visible_collide = True
        interactive_collide = True

        all_shapes = self.space.shapes.copy()

        while (visible_collide or interactive_collide) and trial < tries:

            self.add_scene_element(scene_element)

            visible_collide = False
            interactive_collide = False

            if scene_element.pm_visible_shape is not None:
                collisions = [scene_element.pm_visible_shape.shapes_collide(shape) for shape in all_shapes]
                visible_collide = any([len(collision.points) != 0 for collision in collisions])

            if scene_element.pm_interaction_shape is not None:
                collisions = [scene_element.pm_interaction_shape.shapes_collide(shape) for shape in all_shapes]
                interactive_collide = any([len(collision.points) != 0 for collision in collisions])

            if visible_collide or interactive_collide:
                self._remove_scene_element(scene_element)

            trial += 1

        return not (visible_collide or interactive_collide)

    def _remove_agents(self):

        for agent in self.agents:
            self.remove_agent(agent)

    def remove_agent(self, agent):
        for part in agent.parts:
            self.space.remove(*part.pm_elements)
            part.velocity = [0, 0, 0]
        self.agents.remove(agent)

    def _remove_scene_element(self, scene_element):

        self.space.remove(*scene_element.pm_elements)
        self.scene_elements.remove(scene_element)

        if not scene_element.is_temporary_entity:
            self._disappeared_scene_elements.append(scene_element)

        for elem in self.scene_elements:
            if elem.entity_type is SceneElementTypes.DISPENSER and scene_element in elem.produced_entities:
                elem.produced_entities.remove(scene_element)

        for field in self.fields:
            if scene_element in field.produced_entities:
                field.produced_entities.remove(scene_element)

        if scene_element in self._grasped_scene_elements.keys():
            body_part = self._grasped_scene_elements[scene_element]
            self.space.remove(*body_part.grasped)
            body_part.grasped = []

    def _fields_produce(self):

        for field in self.fields:

            if field.can_produce():
                new_entity = field.produce()
                self.add_scene_element(new_entity)

    def _check_timers(self):

        for entity in self.scene_elements:

            if entity.timed and entity.timer == 0:

                list_remove, list_add = entity.activate(self)

                for entity_removed in list_remove:
                    self._remove_scene_element(entity_removed)

                for entity_added in list_add:
                    self.add_scene_element(entity_added)

    def _release_grasps(self):

        for agent in self.agents:

            for part in agent.parts:
                if not part.is_holding and part.can_grasp:

                    for joint in part.grasped:
                        self.space.remove(joint)
                    part.grasped = []

    def get_scene_element_from_shape(self, pm_shape):
        """
        Returns: Returns the Scene Element associated with the pymunk shape.

        """
        entity = next(iter([e for e in self.scene_elements if pm_shape in e.pm_elements]), None)
        return entity

    def get_agent_from_shape(self, pm_shape):
        """
        Returns: Returns the Agent associated with the pymunk shape.

        """
        for agent in self.agents:
            if agent.owns_shape(pm_shape):
                return agent

        return None

    def _get_closest_agent(self, ent):

        dist_list = [(a.position[0] - ent.position[0])**2 + (a.position[1] - ent.position[1])**2 for a in self.agents]
        index_min_dist = dist_list.index(min(dist_list))
        closest_agent = self.agents[index_min_dist]

        return closest_agent

    def _agent_touches_entity(self, arbiter, space, data):

        agent = self.get_agent_from_shape(arbiter.shapes[0])
        touched_entity = self.get_scene_element_from_shape(arbiter.shapes[1])

        agent.reward += touched_entity.reward

        list_remove, list_add = touched_entity.activate()

        for entity_removed in list_remove:
            self._remove_scene_element(entity_removed)

        for entity_added in list_add:
            self.add_scene_element(entity_added)

        if touched_entity.terminate_upon_contact:
            self.done = True

        return True

    def _agent_interacts(self, arbiter, space, data):

        agent = self.get_agent_from_shape(arbiter.shapes[0])
        body_part = agent.get_bodypart_from_shape(arbiter.shapes[0])
        interacting_entity = self.get_scene_element_from_shape(arbiter.shapes[1])

        if body_part.is_activating:

            agent.reward += interacting_entity.reward

            list_remove, list_add = interacting_entity.activate(body_part)

            for entity_removed in list_remove:
                self._remove_scene_element(entity_removed)

            for entity_added in list_add:
                self.add_scene_element(entity_added)

            if interacting_entity.terminate_upon_contact:
                self.done = True

            body_part.is_activating = False

        return True

    def _agent_grasps(self, arbiter, space, data):

        agent = self.get_agent_from_shape(arbiter.shapes[0])
        body_part = agent.get_bodypart_from_shape(arbiter.shapes[0])
        interacting_entity = self.get_scene_element_from_shape(arbiter.shapes[1])

        if body_part.is_grasping and not body_part.is_holding:

            body_part.is_holding = True

            j_1 = pymunk.PinJoint(interacting_entity.pm_body, body_part.pm_body, (0, 5), (0, -5))
            j_2 = pymunk.PinJoint(interacting_entity.pm_body, body_part.pm_body, (0, -5), (0, 5))
            j_3 = pymunk.PinJoint(interacting_entity.pm_body, body_part.pm_body, (5, 5), (0, 5))
            j_4 = pymunk.PinJoint(interacting_entity.pm_body, body_part.pm_body, (5, -5), (0, 5))

            self.space.add(j_1, j_2, j_3, j_4)
            body_part.grasped = [j_1, j_2, j_3, j_4]

            self._grasped_scene_elements[interacting_entity] = body_part

        return True

    def _agent_enters_zone(self, arbiter, space, data):

        agent = self.get_agent_from_shape(arbiter.shapes[0])
        zone_reached = self.get_scene_element_from_shape(arbiter.shapes[1])

        agent.reward += zone_reached.reward

        if zone_reached.terminate_upon_contact:
            self.done = True

        return True

    def _gem_interacts(self, arbiter, space, data):

        gem = self.get_scene_element_from_shape(arbiter.shapes[0])
        interacting_entity = self.get_scene_element_from_shape(arbiter.shapes[1])

        agent = self._get_closest_agent(gem)
        agent.reward += interacting_entity.reward

        list_remove, list_add = interacting_entity.activate(gem)

        for entity_removed in list_remove:
            self._remove_scene_element(entity_removed)

        for entity_added in list_add:
            self.add_scene_element(entity_added)

        if interacting_entity.terminate_upon_contact:
            self.done = True

        return True

    def _agent_eats(self, arbiter, space, data):

        agent = self.get_agent_from_shape(arbiter.shapes[0])
        body_part = agent.get_bodypart_from_shape(arbiter.shapes[0])
        edible_entity = self.get_scene_element_from_shape(arbiter.shapes[1])

        if body_part.is_eating:

            agent.reward += edible_entity.get_reward()

            self._remove_scene_element(edible_entity)
            completely_eaten = edible_entity.eats()

            if not completely_eaten:
                self.add_scene_element(edible_entity, new_position=False)

            body_part.is_eating = False

        return True

    def _handle_collisions(self):

        h_touch = self.space.add_collision_handler(CollisionTypes.AGENT, CollisionTypes.CONTACT)
        h_touch.pre_solve = self._agent_touches_entity

        h_eat = self.space.add_collision_handler(CollisionTypes.AGENT, CollisionTypes.EDIBLE)
        h_eat.pre_solve = self._agent_eats

        h_interact = self.space.add_collision_handler(CollisionTypes.AGENT, CollisionTypes.INTERACTIVE)
        h_interact.pre_solve = self._agent_interacts

        h_zone = self.space.add_collision_handler(CollisionTypes.AGENT, CollisionTypes.PASSIVE)
        h_zone.pre_solve = self._agent_enters_zone

        h_gem_interactive = self.space.add_collision_handler(CollisionTypes.GEM, CollisionTypes.INTERACTIVE)
        h_gem_interactive.pre_solve = self._gem_interacts

        h_grasp = self.space.add_collision_handler(CollisionTypes.AGENT, CollisionTypes.GRASPABLE)
        h_grasp.pre_solve = self._agent_grasps