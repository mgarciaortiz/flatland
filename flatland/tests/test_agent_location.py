from flatland import playgrounds
import matplotlib.pyplot as plt
import flatland.agents.forward_head as forward_head

from flatland.common.default_entities_parameters import *

def display(img):
    plt.imshow(img)
    plt.axis('off')
    plt.show()


pg = playgrounds.PlaygroundGenerator.create('rooms_2_edible' )

agent_parameters = {
    'starting_position' : {
        'type' : 'static',
        'position' : [124, 34, 0]
            }
}

agent = forward_head.ForwardHeadAgent(agent_parameters)

pg.add_agent(agent)

img = pg.generate_playground_image()
display(img)