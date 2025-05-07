# File that manages input data between the program and the user

# Imports
import os
from planner import Planner

class ProblemDefinition():
    """Class that contains all methods to manage input data"""
    def __init__(self):
        self.event = None
        self.liquid = None
        self.output_path = None
        self.problem_path = None
        self.problem = None
        self.objective = None
        self.available_methods = ["METADATA", "OGAMUS"]
        self.available_actions = [
            "Move Agent",
            "Pickup Object",
            "Open Object",
            "Close Object",
            "Break Object",
            "Cook Object",
            "Slice Object",
            "Toggle On Object",
            "Toggle Off Object",
            "Dirty Object",
            "Clean Object",
            "Fill Object",
            "Empty Object",
            "Use Up Object",
            "Drop Object (Requires holding an object)",
            "Put Object (Requires holding an object)"]

        self.available_scenes = {
            "kitchens": range(1,30+1),
            "living_rooms": range(201, 230+1),
            "bedrooms": range(301, 330+1),
            "bathrooms": range(401, 430+1)
        }

        self.problem_list = []
        self.objective_list = []
        self.method = None
        self.scene_number = None

    @staticmethod
    def _user_choice_in_list(items: list, message: str, print_list: bool = False) -> tuple:
        """Asks the user tho make a choice in a given items list, returning both the index and the item"""
        if print_list:
            for index, item in enumerate(items):
                print(f"[{index}] {item}")
        while True:
            index_str = input(message)
            if index_str.isdigit():
                index = int(index_str)
                if 0 <= index < len(items):
                    return index, items[index]

    def method_selection(self):
        '''Method that allows selecting execution type:
        1. METADATA: Uses data returned by simulator to locate objects and agent positions
        2. OGAMUS: Uses OGAMUS algorithm to scan scenes using pretrained neural networks'''

        chosen_method, _ = self._user_choice_in_list(self.available_methods, "Select the method used to solve the problem: ", print_list=True)
        chosen_method += 1  # because methods are "1" or "2" ...
        chosen_method = str(chosen_method)
        self.set_method(chosen_method)
        return self.method

    def set_method(self, method):
        self.method = method
        

    def scene_selection(self):
        """Method that allows selection of the scene"""
        invalid_input = True
        while invalid_input:
            print("----SCENE----")
            print("[1-30] - Kitchens")
            print("[201-230] - Living Rooms")
            print("[301-330] - Bedrooms")
            print("[401-430] - Bathrooms")
            print("---------------")

            user_input = input("Select a scene: ")
            if not user_input.isdigit():
                continue

            user_number = int(user_input)
            for scene_category in self.available_scenes:
                if user_number in self.available_scenes[scene_category]:
                    invalid_input = False
                    self.scene_number = str(user_number)

        return self.scene_number

    def set_scene(self, scene_number):
        self.scene_number = str(scene_number)

    def paths_selection(self, iteracion):
        """Method that specifies problem and output paths"""
        self.problem_path = f'./pddl/problems/problem{iteracion}.pddl'
        self.output_path = f'./pddl/outputs/problem{iteracion}.txt'

        return self.problem_path, self.output_path

    def problem_selection(self, event):
        """Method that allows selecting problems and objectives"""
        self.liquid = 'coffee'
        self.event = event
        invalid_input = True

        chosen_action, chosen_action_name = self._user_choice_in_list(self.available_actions, "Select an action: ", print_list=True)
        aux = chosen_action + 1

        while invalid_input:
            holding = any(x["isPickedUp"] for x in event.metadata["objects"])

            if aux != "" and (1 <= int(aux) <= 14):
                invalid_input = False
            elif aux != "" and (15 <= int(aux) <= 16) and holding:
                invalid_input = False
            else:
                print("Please, input a valid action\n")
                chosen_action, chosen_action_name = self._user_choice_in_list(self.available_actions, "Select an action: ")
                aux = chosen_action + 1

        print(f"Chosen action: {chosen_action_name}")
        return self.set_problem(event, aux)

    def set_problem(self, event, problem_number: str):
        # Establecer parámetros en caso de que se seleccione problema de movimiento

        if (problem_number is str and not problem_number.isdigit()) \
                or int(problem_number) < 0 \
                or int(problem_number) > 15:
            raise ValueError("problem_number must be a string containing a number between 0 and 15")  # I know...

        aux = int(problem_number) + 1
        if str(aux) == '1':
            self.problem = "move"
            print("----OBJECTIVE----")
            positions = event.metadata["actionReturn"]
            i = 0
            for pos in positions:
                print(f'[{i}] - {pos}')
                i += 1
            print("----------------")
            aux2 = input("Select the goal position: ")
            self.objective = positions[int(aux2)]
            print("")
            print(f'Selected goal position is: {self.objective}')

        # Establecer parámetros en caso de que se seleccione problema de pickup
        if str(aux) == '2':
            self.object_selection("pickup", "pickupable", "isPickedUp", False)

        if str(aux) == '3':
            self.object_selection("open", "openable", "isOpen", False)

        if str(aux) == '4':
            self.object_selection("close", "openable", "isOpen", True)
        
        if str(aux) == '5':
            self.object_selection("break", "breakable", "isBroken", False)
        
        if str(aux) == '6':
            self.object_selection("cook", "cookable", "isCooked", False)

        if str(aux) == '7':
            self.object_selection("slice", "sliceable", "isSliced", False)

        if str(aux) == '8':
            self.object_selection("toggleon", "toggleable", "isToggled", False)

        if str(aux) == '9':
            self.object_selection("toggleoff", "toggleable", "isToggled", True)

        if str(aux) == '10':
            self.object_selection("dirty", "dirtyable", "isDirty", False)

        if str(aux) == '11':
            self.object_selection("clean", "dirtyable", "isDirty", True)
        
        if str(aux) == '12':
            self.object_selection("fill", "canFillWithLiquid", "isFilledWithLiquid", False, True)

        if str(aux) == '13':
            self.object_selection("empty", "canFillWithLiquid", "isFilledWithLiquid", True)
        
        if str(aux) == '14':
            self.object_selection("useup", "canBeUsedUp", "isUsedUp", False)
        
        if str(aux) == '15':
            holding = any(x["isPickedUp"] for x in event.metadata["objects"])
            if not holding:
                raise Exception("Action 'drop' requires holding an item")
            self.object_selection("drop", "pickupable", "isPickedUp", True)
        
        if str(aux) == '16':
            holding = any(x["isPickedUp"] for x in event.metadata["objects"])
            if not holding:
                raise Exception("Action 'put' requires holding an item")
            self.object_selection("put", "receptacle", "receptacle", True)
            
        return self.problem, self.objective, self.liquid


    def _get_objects(self, condition1, condition2, condition2_res, select_liquid=False):
        """Given the specified problem type and conditions it retuns a list of objects currently in scene that meet thos criteria"""
        return [x for x in self.event.metadata["objects"] if x[condition1] and x[condition2] == condition2_res]

    def object_selection(self, problem_type, condition1, condition2, condition2_res, select_liquid=False):
        """Method that contains the objective selection of most of the problems"""
        self.problem = problem_type
        possible_objects = self._get_objects(condition1, condition2, condition2_res)

        if not possible_objects or len(possible_objects) == 0:
            print("There aren't any objectives for this action. Select another or switch the scene\n")
            return self.problem_selection(self.event)

        print("----OBJECTIVE----")
        for (i, obj) in enumerate(possible_objects):
            print(f'[{i}] - {obj["objectId"]}')
        print("----------------")

        # Ask the user to choose an object
        _, self.objective = self._user_choice_in_list(possible_objects, "Select the objective: ")
        print(f'\nSelected objective is: {self.objective["objectId"]} {self.objective["name"]}\n')

        if select_liquid:
            print("----LIQUID----")
            print("[1] - Coffee")
            print("[2] - Wine")
            print("[3] - Water")
            print("----------------")
            inp = input(f'Select liquid to fill objective with: ')

            if str(inp) == '1':
                self.liquid = 'coffee'
            elif str(inp) == '2':
                self.liquid = 'wine'
            elif str(inp) == '3':
                self.liquid = 'water'

        return None

    def problem_selection_ogamus(self):
        """Method that allows user to select problems to be solved with OGAMUS"""
        invalid_input = True
        while invalid_input:
            print("----ACTION----")
            print("[1] - Get Close To Object")
            print("[2] - Pickup Object")
            print("[3] - Open Object")
            print("[4] - Close Object")
            print("[5] - Break Object")
            print("[6] - Cook Object")
            print("[7] - Slice Object")
            print("[8] - Toggle On Object")
            print("[9] - Toggle Off Object")
            print("[10] - Dirty Object")
            print("[11] - Clean Object")
            print("[12] - Fill Object")
            print("[13] - Empty Object")
            print("[14] - Use Up Object")
            print("[15] - Drop Object (Requires holding an object)")
            print("[16] - Put Object (Requires holding an object)")
            print("----------------")
            aux = input("Select an action: ")
            print("")
            if (1 <= int(aux) <= 16):
                invalid_input = False
            else:
                print("Please, input a valid action\n")
        
        problems_ogamus = ["get_close_to", "pickup", "open", "close", "break", "cook", "slice", "toggleon", "toggleoff", "dirty", "clean", "fill", "empty", "useup", "drop", "put"]
        self.problem = problems_ogamus[int(aux) - 1]
        self.problem_list.append(self.problem)

        self.object_selection_ogamus()

        print("")
        condition = input('Do you want to execute more actions in this environment? [Y/n]: ')
        print("")
        if condition == 'Y':
            self.problem_selection_ogamus()

        return self.problem_list, self.objective_list
    
    def object_selection_ogamus(self):
        '''Method that allows selecting the objective of OGAMUS problem'''
        if self.problem == "get_close_to":
            possible_objects = ["alarmclock", "aluminumfoil", "apple", "baseballbat", "book", "boots", "basketball",
                    "bottle", "bowl", "box", "bread", "butterknife", "candle", "cd", "cellphone", "peppershaker",
                    "cloth", "creditcard", "cup", "dishsponge", "dumbbell", "egg", "fork", "handtowel",
                    "kettle", "keychain", "knife", "ladle", "laptop", "lettuce", "mug", "newspaper",
                    "pan", "papertowel", "papertowelroll", "pen", "pencil", "papershaker", "pillow", "plate", "plunger",
                    "pot", "potato", "remotecontrol", "saltshaker", "scrubbrush", "soapbar", "soapbottle",
                    "spatula", "spoon", "spraybottle", "statue", "tabletopdecor", "teddybear", "tennisracket",
                    "tissuebox", "toiletpaper", "tomato", "towel", "vase", "watch", "wateringcan", "winebottle", "armchair", "bathtub", "bathtubbasin", "bed", "bowl", "box", "cabinet", "coffeemachine",
                   "coffeetable", "countertop", "desk", "diningtable", "drawer", "fridge", 
                   "garbagecan", "handtowelholder", "laundryhamper", "microwave", "mug", "ottoman", "pan",
                   "plate", "pot", "safe", "shelf", "sidetable", "sinkbasin", "sofa", "toaster",
                   "toilet", "toiletpaperhanger", "towelholder", "tvstand", "stoveburner", "blinds", "book", "box", "cabinet", "drawer", "fridge", "kettle", "laptop", "microwave",
                 "safe", "showercurtain", "showerdoor", "toilet"]

        elif self.problem == "pickup" or self.problem == "drop":
            possible_objects = ["alarmclock", "aluminumfoil", "apple", "baseballbat", "book", "boots", "basketball",
                    "bottle", "bowl", "box", "bread", "butterknife", "candle", "cd", "cellphone", "peppershaker",
                    "cloth", "creditcard", "cup", "dishsponge", "dumbbell", "egg", "fork", "handtowel",
                    "kettle", "keychain", "knife", "ladle", "laptop", "lettuce", "mug", "newspaper",
                    "pan", "papertowel", "papertowelroll", "pen", "pencil", "papershaker", "pillow", "plate", "plunger",
                    "pot", "potato", "remotecontrol", "saltshaker", "scrubbrush", "soapbar", "soapbottle",
                    "spatula", "spoon", "spraybottle", "statue", "tabletopdecor", "teddybear", "tennisracket",
                    "tissuebox", "toiletpaper", "tomato", "towel", "vase", "watch", "wateringcan", "winebottle"]
                    
        elif self.problem == "open" or self.problem == "close":
            possible_objects = ["blinds", "book", "box", "cabinet", "drawer", "fridge", "kettle", "laptop", "microwave",
                 "safe", "showercurtain", "showerdoor", "toilet"]

        elif self.problem == "put":
            possible_objects = ["armchair", "bathtub", "bathtubbasin", "bed", "bowl", "box", "cabinet", "coffeemachine",
                   "coffeetable", "countertop", "desk", "diningtable", "drawer", "fridge",
                   "garbagecan", "handtowelholder", "laundryhamper", "microwave", "mug", "ottoman", "pan",
                   "plate", "pot", "safe", "shelf", "sidetable", "sinkbasin", "sofa", "toaster",
                   "toilet", "toiletpaperhanger", "towelholder", "tvstand", "stoveburner"]

        elif self.problem == "break":
            possible_objects = ["bottle", "bowl", "cellphone", "cup", "egg", "laptop", "television", "mirror", "mug", "plate",
                    "showerdoor", "statue", "vase", "window", "winebottle"]

        elif self.problem == "cook":
            possible_objects = ["breadsliced", "eggcracked", "potato", "potatosliced"]
        
        elif self.problem == "slice":
            possible_objects = ["apple", "bread", "egg", "lettuce", "potato", "tomato"]
        
        elif self.problem == "toggleon" or self.problem == "toggleoff":
            possible_objects = ["candle", "cellphone", "coffeemachine", "desklamp", "faucet", "floorlamp", "laptop", "lightswitch", "microwave", "showerhead",
                                "stoveburner", "stoveknob", "television", "toaster"]
            
        elif self.problem == "dirty" or self.problem == "clean":
            possible_objects = ["bed", "bowl", "cloth", "cup", "mirror", "mug", "pan", "plate", "pot"]

        elif self.problem == "fill" or self.problem == "empty":
            possible_objects = ["bottle", "bowl", "cup", "houseplant", "kettle", "mug", "pot", "wateringcan", "winebottle"]

        elif self.problem == "useup":
            possible_objects = ["papertowelroll", "soapbottle", "tissuebox", "toiletpaper"]

        print("----OBJECTIVE----")
        i = 0
        for obj in possible_objects:
            print(f'[{i}] - {obj}')
            i += 1
        print("----------------")
        aux2 = input("Select the objective: ")
        self.objective = possible_objects[int(aux2)]
        self.objective_list.append(self.objective)
    
    def problem_selection_ogamus_input(self, input):
        '''Method that executes and reads PDDL input files for OGAMUS'''
        # We call the planner and save the input in /pddl/outputs/input_plan.txt
        planificador = Planner(input, "./pddl/outputs/input_plan.txt", "pickup", 1, 3, True, True)

        # Extract the plan        
        raw_plan = planificador.get_plan()
        start_index = raw_plan.find("0:")
        end_index = raw_plan.find("time")

        # Get actions split by lines
        plan = raw_plan[start_index:end_index]
        plan = plan.splitlines()
        
        list_plan = []

        # Remove blank spaces
        for act in plan:
            if (act.find(":") == -1) or (not act):
                plan.remove(act)
            index = act.find(":")
            act = act[:index].replace(" ", "") + act[index:]
            list_plan.append(act)
        
        # Remove last position if empty
        if list_plan[-1] == ' ':
            list_plan.pop()

        # Cycle through each action and parse it to add problems and objectives to arrays
        for act in list_plan:
            if act.find("BASICACTION") != -1:
                start_index = act.find("(") + 15
                act2 = act[start_index:]
                end_index = act2.find(" ")
                problem_name = act2[:end_index]
                end_index2 = act2.find(")")
                objective_name = act2[end_index+1:end_index2]
            
                self.problem_list.append(problem_name.lower())
                self.objective_list.append(objective_name.lower())
        
        print(" ")
        print(self.problem_list)
        print(self.objective_list)
        print(" ")

        return self.problem_list, self.objective_list


        
