"""
Default definitions
"""

from enum import IntEnum, Enum, auto

#pylint: disable=missing-class-docstring

SIMULATION_STEPS = 10
SPACE_DAMPING = 0.9


class SceneElementTypes(Enum):

    FIELD = 'field'
    DISPENSER = 'dispenser'


class CollisionTypes(IntEnum):

    AGENT = 1
    CONTACT = 2
    INTERACTIVE = 3
    PASSIVE = 4
    GEM = 5
    EDIBLE = 6
    GRASPABLE = 7
    ACTIVATED_BY_GEM = 8
    TELEPORT = 9


class ControllerTypes(Enum):

    KEYBOARD = 1
    RANDOM = 2
    EXTERNAL = 3


class ActionTypes(IntEnum):

    DISCRETE = auto()
    CONTINUOUS_CENTERED = auto()
    CONTINUOUS_NOT_CENTERED = auto()

    LONGITUDINAL_FORCE = auto()
    LATERAL_FORCE = auto()
    ANGULAR_VELOCITY = auto()

    GRASP = auto()
    EAT = auto()
    ACTIVATE = auto()


class SensorTypes(IntEnum):

    RGB = 1


class KeyTypes(IntEnum):

    PRESS_HOLD = 1
    PRESS_ONCE = 2


class SensorModality(Enum):
    VISUAL = auto()
    SEMANTIC = auto()
    ROBOTIC = auto()
    UNDEFINED = auto()


class Detection:

    def __init__(self, entity, distance, angle):

        self.entity = entity
        self.distance = distance
        self.angle = angle

geometric_shapes = {'line': 2, 'circle': 60, 'triangle': 3,
                    'square': 4, 'pentagon': 5, 'hexagon': 6}
