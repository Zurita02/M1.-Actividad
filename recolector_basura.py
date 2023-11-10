from mesa import Agent, Model # type: ignore
from mesa.space import SingleGrid # type: ignore
from mesa.time import SimultaneousActivation # type: ignore
from mesa.visualization.modules import CanvasGrid # type: ignore
from mesa.visualization.ModularVisualization import ModularServer # type: ignore
import numpy as np
import time

def random_grid_cells(width, height, per):
    cells = []
    grid = width * height
    total_cells = int(grid * (per / 100))

    for _ in range(total_cells):
        while True:
            cell = (np.random.randint(0, height), np.random.randint(0, width))
            if cell not in cells and cell != (1, 1):
                cells.append(cell)
                break
    return cells

class Trash(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.next_state = None

class Cleaner(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.next_state = None
    
    def step(self):
        x, y = self.pos
        neighbours = [(x + dx, y + dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1]]
        next_x, next_y = self.random.choice(neighbours)
        if 0 <= next_x < self.model.grid.width and 0 <= next_y < self.model.grid.height:
            if self.model.grid.is_cell_empty((next_x, next_y)):
                self.model.grid.move_agent(self, (next_x, next_y))
            else: 
                cell_contents = self.model.grid.get_cell_list_contents([(next_x, next_y)])
                trash_agents = [agent for agent in cell_contents if isinstance(agent, Trash)]

                if trash_agents:
                    trash = trash_agents[0]
                    self.model.grid.remove_agent(trash)
                    self.model.schedule.remove(trash)
                    self.model.grid.move_agent(self, (next_x, next_y))


class CleaningTrashModel(Model):
    def __init__(self, width, height, count_agents, per_trash, max_time):
        self.grid = SingleGrid(width, height, True)
        self.schedule = SimultaneousActivation(self)
        self.running = True
        self.count_agents = count_agents
        self.id = 0
        self.current_time = 0
        self.max_time = max_time
        self.start_time = time.time()
        self.cleaned_cells = 0
        self.total_cells = width * height
        self.count_steps = 0
        
        # Trash creation
        trash_cells = random_grid_cells(width, height, per_trash)
        for x, y in trash_cells:
            trash = Trash((x, y), self)
            self.grid.place_agent(trash, (x, y))
            self.schedule.add(trash) 
        
        cleaner = Cleaner(self.id, self)
        self.grid.place_agent(cleaner, (1, 1))
        self.schedule.add(cleaner)
        self.id +=1

    def step(self):
        self.schedule.step()

        self.current_time = time.time() - self.start_time

        if self.current_time >= self.max_time:
            self.running = False

        if not any(isinstance(agent, Trash) for agent in self.schedule.agents):
            self.running = False

        cleaned_cells = sum(1 for agent in self.schedule.agents if isinstance(agent, Cleaner))
        self.cleaned_cells = cleaned_cells

        # Cleaners creation
        if self.grid.is_cell_empty((1, 1)) and self.id < self.count_agents:
            next_cleaner = Cleaner(self.id, self)
            self.grid.place_agent(next_cleaner, (1, 1))
            self.schedule.add(next_cleaner)
            self.id +=1

        self.count_steps += 1

if __name__ == "__main__":
    
    def agent_portrayal(agent):
        if isinstance(agent, Cleaner):
            portrayal = {"Shape": "circle",
                        "Filled": "true",
                        "Layer": 0,
                        "Color": "green",
                        "r": 1}
        else:
            portrayal = {"Shape": "circle",
                        "Filled": "true",
                        "Layer": 0,
                        "Color": "gray",
                        "r": 0.5}
        return portrayal

    width = 25
    height = 25
    count_agents = 15
    per_trash = 20
    max_time = 60
    grid = CanvasGrid(agent_portrayal, width, height, 500, 500)
    server = ModularServer(CleaningTrashModel,
                        [grid],
                        "Robots Limpiadores Model",
                        {"width":width, "height":height, 
                        "count_agents" : count_agents, "per_trash" : per_trash, 
                        "max_time" : max_time})
    server.port = 8521 # The default
    server.launch()

    model = server.model
    # Cleaned percentage of the total dirty cells
    clean_cells = (model.cleaned_cells / model.total_cells) * 100
    agent_moves = model.count_steps * model.count_agents
    print(f"Clean cells percentage: {clean_cells}%")
    print(f"Agent moves: {agent_moves}")
