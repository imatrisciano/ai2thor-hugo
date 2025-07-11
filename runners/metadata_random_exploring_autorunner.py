import random

from tqdm import tqdm

from problem_definition import ProblemDefinition
from runners.metadata_shallow_autorunner import MetadataShallowAutorunner


class MetadataRandomExploringAutorunner(MetadataShallowAutorunner):
    def __init__(self, inputs: ProblemDefinition, exploring_repetitions: int, exploring_depth: int):
        super().__init__(inputs)
        self.exploring_repetitions = exploring_repetitions
        self.exploring_depth = exploring_depth

        self.explored_actions = 0
        self.successful_actions = 0

    def run(self):
        """Explores each of the available scenes and tries to run every action"""
        print("Autorunning METADATA mode...")
        print(f"Current action exploring depth is {self.exploring_depth}")
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

        # make a step in the scene so we can grab the event and explore what's in the scene
        event = self.controller.step(action="GetReachablePositions")
        self.inputs.event = event

        allowed_actions = self.inputs.get_allowed_actions(event)
        # pick one of the actions
        for action_number, action_name in enumerate(allowed_actions):
            print(f"\t|\t> Exploring {action_name}")
            if action_number != 0:  # the first action is MOVE, we are not interested in exploring this option
                self.explored_actions = 0
                self.successful_actions = 0
                for _ in tqdm(range(self.exploring_repetitions)):
                    self._autorun_explore_action_in_scene(event, action_number, action_name)
                    self._reload_scene()
                    self.inputs.event = event
                # print(f"\r\t|\t|\t> {self.successful_actions}/{self.explored_actions} successful actions")

    def _autorun_explore_action_in_scene(self, event, action_number, action_name):
        # pick a random target and then keep picking random actions and targets
        for _ in range(self.exploring_depth):
            self.inputs.set_action_number(action_number)
            self.current_action_name = action_name
            action_targets, optional_liquids = self.inputs.get_problem_targets(event, action_number)
            target_has_liquid = optional_liquids is not None

            # if the action can be executed (there are targets) and the action is not MOVE
            if len(action_targets) > 0:
                # pick a random target
                random_target = random.sample(action_targets, 1)[0]
                self.explored_actions += 1
                # execute the action on said target
                if target_has_liquid:
                    for liquid in self.inputs.liquids:
                        # print(f"\t|\t|\t> Running {action_name} on object {target['name']} and liquid {liquid}")
                        if self._autorun_run_action_on_target(event, random_target, liquid):
                            self.successful_actions += 1
                            # update "event" so the next iteration is based on the updated world status
                            event = self.controller.last_event
                            self.inputs.event = event
                else:
                    # print(f"\t|\t|\t> Running {action_name} on object {target['name']}")
                    if self._autorun_run_action_on_target(event, random_target):
                        self.successful_actions += 1
                        # update "event" so the next iteration is based on the updated world status
                        event = self.controller.last_event
                        self.inputs.event = event

            # after the action was executed, reload the list of available actions
            allowed_actions = self.inputs.get_allowed_actions(event)
            if len(allowed_actions) > 0:
                allowed_actions = allowed_actions[1:]  # remove the first action from the pool ("MOVE")
            # pick a random action
            action_name = random.sample(allowed_actions, 1)[0]
            action_number = self.inputs.available_actions.index(action_name)


