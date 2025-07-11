from tqdm import tqdm

from aux import printLastActionStatus, printAgentStatus, printObjectStatus, get_object_by_id, get_changed_properties
from parser_ai2thor_pddl import Ai2ThorPDDLParsingException
from parser_pddl_ai2thor import PddlAi2thorParsingException
from planner import PlannerTimedOutException
from problem_definition import ProblemDefinition
from runners.metadata_runner import MetadataRunner


class MetadataShallowAutorunner(MetadataRunner):
    def __init__(self, inputs: ProblemDefinition):
        super().__init__(inputs)

    def run(self):
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

        event = self.controller.step(
            action="GetReachablePositions")  # make a step in the scene so we can grab the event and explore what's in the scene
        self.inputs.event = event

        allowed_actions = self.inputs.get_allowed_actions(event)
        # pick one of the actions
        for action_number, action_name in enumerate(allowed_actions):
            print(f"\t|\t> Exploring {action_name}")
            if action_number != 0:  # the first action is MOVE, we are not interested in exploring this option
                self._autorun_explore_action_in_scene(event, action_number, action_name)

    def _autorun_explore_action_in_scene(self, event, action_number, action_name):
        self.inputs.set_action_number(action_number)
        self.current_action_name = action_name
        action_targets, optional_liquids = self.inputs.get_problem_targets(event, action_number)
        target_has_liquid = optional_liquids is not None

        successful_actions = 0
        # execute said actions on each object in the scene, resetting the scene between executions
        for target in tqdm(action_targets):
            if target_has_liquid:
                for liquid in self.inputs.liquids:
                    # print(f"\t|\t|\t> Running {action_name} on object {target['name']} and liquid {liquid}")
                    if self._autorun_run_action_on_target(event, target, liquid):
                        successful_actions += 1
            else:
                # print(f"\t|\t|\t> Running {action_name} on object {target['name']}")
                if self._autorun_run_action_on_target(event, target):
                    successful_actions += 1

            self._reload_scene()

        print(f"\r\t|\t|\t> ######## {successful_actions}/{len(action_targets)} successful actions")

    def _get_file_paths(self):
        problem_path, output_path = self.inputs.paths_selection(self.action_counter)
        filename = f"scene_{self.current_scene_number}_{self.action_counter}.json"

        return problem_path, output_path, filename

    def _autorun_run_action_on_target(self, event, objective, liquid="coffee") -> bool:
        self.inputs.set_objective(objective)
        self.inputs.set_liquid(liquid)
        self.action_counter += 1

        print_success: bool = False
        print_failures: bool = False

        problem_path, output_path, filename = self._get_file_paths()
        problem = self.inputs.problem

        try:
            before_world_status = self.controller.last_event

            if problem == "drop":
                self.controller.step(action="DropHandObject")
            if problem == "put":
                held_object = None
                current_objects = self.inputs.event.metadata["objects"]
                for obj in current_objects:
                    if obj["isPickedUp"]:
                        held_object = obj
                        break
                if held_object is not None:
                    #held_object_id = held_object["objectId"]
                    receptacle_object_id = objective["objectId"]
                    self.controller.step(dict(
                        action='PutObject',
                        #objectId=held_object_id,
                        #receptacleObjectId=receptacle_object_id))
                        objectId=receptacle_object_id))
            else:
                self._get_and_run_plan(event, self.action_counter, liquid, objective, output_path, problem,
                                       problem_path)

            after_world_status = self.controller.last_event

            # self.find_changed_properties(before_world_status, after_world_status)

            # Save action data on disk
            action_description = self._build_action_result_obj(before_world_status, after_world_status)
            self.object_store.store(filename, action_description)

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

    def find_changed_properties(self, before_world_status, after_world_status):
        for before_obj in before_world_status.metadata["objects"]:
            object_id = before_obj["objectId"]
            after_obj = get_object_by_id(after_world_status.metadata["objects"], object_id)
            if after_obj is None:
                print(f"Object {object_id} is not in scene anymore")
            else:
                changed_properties = get_changed_properties(before_obj, after_obj)
                if len(changed_properties) > 0:
                    print(f"Listing changed properties for object {object_id} - {before_obj['name']}")
                    print(changed_properties)

    def _build_action_result_obj(self, before_world_status, after_world_status) -> dict:
        obj = {
            "scene_number": self.current_scene_number,
            "action_name": self.current_action_name,
            "action_counter": self.action_counter,
            "problem": self.inputs.problem,
            "problem_path": self.inputs.problem_path,
            "action_objective_id": self.inputs.objective['objectId'],
            "liquid": self.inputs.liquid,
            "before_world_status": before_world_status.metadata,
            "after_world_status": after_world_status.metadata
        }
        return obj
