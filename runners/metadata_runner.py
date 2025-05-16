from ai2thor.controller import Controller
from ai2thor.platform import CloudRendering
from ai2thor.util.metrics import (get_shortest_path_to_object_type)
from tqdm import tqdm

from problem_definition import ProblemDefinition
from parser_ai2thor_pddl import ParserAI2THORPDDL, Ai2ThorPDDLParsingException
from parser_pddl_ai2thor import ParserPDDLAI2THOR, PddlAi2thorParsingException
from planner import Planner, PlannerTimedOutException
from aux import printAgentStatus, printLastActionStatus, createCamera, printObjectStatus, removeResultFolders, isObjectOnScene, ensureDirectoriesExist




class MetadataRunner:
    def __init__(self, inputs: ProblemDefinition):
        self.inputs = inputs
        self.controller = None
        self.action_counter = 1
        self.current_scene_number = None


        self.ai2thor_to_pddl_parser = ParserAI2THORPDDL()
        self.pddl_to_ai2thor_parser = ParserPDDLAI2THOR()


    def _prepare_scene(self, scene_number):
        # Initial start of the environment
        self.controller = Controller(
            agentMode="default",  # Agent used is iTHOR -> default
            visibilityDistance=1.5,  # Visibility distance
            scene="FloorPlan" + str(scene_number),
            gridSize=0.25,  # Step size
            snapToGrid=True,
            rotateStepDegrees=90,
            renderDepthImage=False,
            renderInstanceSegmentation=False,
            width=224,  # Controller width
            height=224,  # Controller height
            fieldOfView=90,  # Controller field of view
            platform=CloudRendering  # Headless mode
        )

        # We create a camera on top of the scene and save an image
        self.current_scene_number = scene_number
        createCamera(self.controller)

    def _reload_scene(self):
        self.controller.stop()
        self._prepare_scene(self.current_scene_number)

    def run(self):
        scene_number = self.inputs.scene_selection()
        self._prepare_scene(scene_number)

        # Loop that allows to repeat actions on the same environment
        loop = 'Y'
        while loop == 'Y':
            # Set up problem and output path
            problem_path, output_path = self.inputs.paths_selection(self.action_counter)

            # Execution of an action inside the controller. GetReachablePositions allow us to get all the positions where the agent is allowed to be in the scene
            event = self.controller.step(action="GetReachablePositions")

            # Ask user for problem and objective
            problem, objective, liquid = self.inputs.problem_selection(event)

            # If the problem selected is drop there is no need to plan anything. Execute the action directly. Otherwise parse the problem and generate a plan.
            if problem == "drop":
                event = self.controller.step(action="DropHandObject")
            else:
                self._get_and_run_plan(event, self.action_counter, liquid, objective, output_path, problem, problem_path)

            # Final state visualization depending on the type of the problem
            printLastActionStatus(self.controller.last_event)
            if problem == 'move':
                printAgentStatus(self.controller.last_event)
            else:
                printObjectStatus(self.controller.last_event, objective)

            # Ask if the user wants to execute another action. If not, stop the program.
            loop = input('Do you want to execute another action? [Y/n]: ')
            self.action_counter += 1


    def autorun(self):
        """Explores each of the available scenes and tries to run every action"""
        print("Autorunning METADATA mode...")
        print("Here are the available scenes:")
        print(self.inputs.available_scenes)
        print()

        for scene_range_name in self.inputs.available_scenes:
            scene_range = self.inputs.available_scenes[scene_range_name]
            for scene_number in scene_range:
                print(f"> Exploring {scene_range_name} #{scene_number}")
                self._autorun_explore_scene(scene_number)

    def _autorun_explore_scene(self, scene_number):
        self.inputs.set_scene(scene_number)
        self._prepare_scene(scene_number)

        event = self.controller.step(action="GetReachablePositions")  # make a step in the scene so we can grab the event and explore what's in the scene
        self.inputs.event = event

        allowed_actions = self.inputs.get_allowed_actions(event)
        for action_number, action_name in enumerate(allowed_actions):
            print(f"\t|\t> Exploring {action_name}")
            if action_number != 0: #the first action is MOVE, we are not interested in exploring this option
                self._autorun_explore_action_in_scene(event, action_number, action_name)

    def _autorun_explore_action_in_scene(self, event, action_number, action_name):
        self.inputs.set_action_number(action_number)
        action_targets, optional_liquids = self.inputs.get_problem_targets(event, action_number)
        target_has_liquid = optional_liquids is not None

        successful_actions = 0
        for target in tqdm(action_targets):
            if target_has_liquid:
                for liquid in self.inputs.liquids:
                    #print(f"\t|\t|\t> Running {action_name} on object {target['name']} and liquid {liquid}")
                    if self._autorun_run_action_on_target(event, target, liquid):
                        successful_actions += 1
            else:
                #print(f"\t|\t|\t> Running {action_name} on object {target['name']}")
                if self._autorun_run_action_on_target(event, target):
                    successful_actions += 1

            self._reload_scene()

        print(f"\r\t|\t|\t> ######## {successful_actions}/{len(action_targets)} successful actions")

    def _autorun_run_action_on_target(self, event, objective, liquid="coffee") -> bool:
        self.inputs.set_objective(objective)
        self.inputs.set_liquid(liquid)
        self.action_counter += 1

        print_success: bool = False
        print_failures: bool = False

        problem_path, output_path = self.inputs.paths_selection(self.action_counter)
        problem = self.inputs.problem

        try:
            if problem == "drop":
                self.controller.step(action="DropHandObject")
            else:
                self._get_and_run_plan(event, self.action_counter, liquid, objective, output_path, problem, problem_path)

            if print_success:
                printLastActionStatus(self.controller.last_event)
                if problem == 'move':
                    printAgentStatus(self.controller.last_event)
                else:
                    printObjectStatus(self.controller.last_event, objective)

            return True
        except Ai2ThorPDDLParsingException as e:
            if print_failures:
                print(f"\t|\t|\t|\t>Action failed (ai2thor -> pddl parsing failed): {e}")
        except PddlAi2thorParsingException as e:
            if print_failures:
                print(f"\t|\t|\t|\t>Action failed (pddl -> ai2thor parsing failed): {e}")
        except PlannerTimedOutException:
            if print_failures:
                print("\t|\t|\t|\t>Action failed (planner timed out)")
        except Exception as e:
            if print_failures:
                print(f"\t|\t|\t|\t>Action failed {e}")

        return False


    def _get_and_run_plan(self, event, iteration, liquid, objective, output_path, problem, problem_path):
        # Using the parser, we translate the simulator state to a PDDL problem
        self.ai2thor_to_pddl_parser.parse(event, problem_path, problem, objective, self.controller)

        # Execute the planner with the problem file generated and the corresponding domain (based on selected action)
        plan = Planner(problem_path, output_path, problem, 1, 3, print=False, ogamus=False)
        actual_plan = plan.get_plan()

        # Parse and execute plan into actions
        self.pddl_to_ai2thor_parser.parse(actual_plan, self.controller, iteration, liquid)
