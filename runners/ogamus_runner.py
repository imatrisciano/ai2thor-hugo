import json
import os.path
import shutil
import sys
from ai2thor.controller import Controller
from exec_ogamus import ExecOgamus
from aux import printAgentStatus, printLastActionStatus, createCamera, printObjectStatus, removeResultFolders, isObjectOnScene, ensureDirectoriesExist


class OgamusRunner:
    def __init__(self, inputs):
        self.inputs = inputs
        self.DATASET = 'Datasets/test_set_ogn_ithor.json'
        self.LOG = "Results/test_set_ogn_ithor_steps200/episode_0/log.txt"

    def run(self):
        # Compute auxiliary params for OGAMUS execution
        # hfov = 79 / 360. * 2. * np.pi
        # vfov = 2. * np.arctan(np.tan(hfov / 2) * 224 / 224)
        # vfov = np.rad2deg(vfov)

        scene_number = self.inputs.scene_selection()

        # Controller start
        print("*STARTING ENVIRONMENT*\n")
        controller = Controller(
            renderDepthImage=1,
            renderObjectImage=True,
            visibilityDistance=1.5,
            gridSize=0.25,
            rotateStepDegrees=45,
            scene="FloorPlan" + str(scene_number),
            continuousMode=True,
            snapToGrid=False,
            width=224,
            height=224,
            fieldOfView=90,
            agentMode='default'
        )

        # We create a camera on top of the scene and save an image
        createCamera(controller)

        # We get initial positions of the agent to pass it to OGAMUS
        event = controller.step("Pass")
        agent_pos = event.metadata["agent"]["position"]
        agent_rot = event.metadata["agent"]["rotation"]
        agent_hor = event.metadata["agent"]["cameraHorizon"]
        print("*ENVIRONMENT SUCCESSFULLY STARTED*\n")

        # Reads problems from CLI or arguments if a PDDL problem is passed.
        if len(sys.argv) == 2:
            problem_list, objective_list = self.inputs.problem_selection_ogamus_input(
                input=sys.argv[1])
        elif len(sys.argv) == 1:
            problem_list, objective_list = self.inputs.problem_selection_ogamus()
        else:
            print("Input a valid PDDL problem file as argument or leave args empty.\n")
            exit()

        # Loop that executes as many times as problems are defined
        iteration = 0
        for problem in problem_list:

            # We create the dictionary to be inserted into the JSON that OGAMUS reads. It contains the scene info previously extracted and the objective
            dictionary = [{
                "episode": 1,
                "scene": "FloorPlan" + scene_number,
                "goal": "(exists (?o1 - " + objective_list[iteration] + ") (and (viewing ?o1) (close_to ?o1)))",
                "agent_position": agent_pos,
                "agent_rotation": agent_rot,
                "initial_orientation": agent_rot['y'],
                "initial_horizon": agent_hor,
                "agent_is_standing": True,
                "agent_in_high_friction_area": False,
                "agent_fov": 90,
                "shortest_path": [
                    {
                        "x": -1.0,
                        "y": 0.901863694190979,
                        "z": 2.0
                    }
                ],
                "shortest_path_length": 0
            }]

            # Modify json with scene info
            json_object = json.dumps(dictionary, indent=4)
            with open(self.DATASET, "w") as f:
                f.write(json_object)

            # Call to ogamus to find the objective
            # controller = ogamus.main(controller)

            # Check if OGAMUS has found the objective. If plan has 200 steps -> objective not found.
            if os.path.exists(self.LOG):
                with open(self.LOG, "r") as f:
                    log_str = f.read()
                    if log_str.find("200:Stop") != -1:
                        print(
                            "No se ha encontrado el objetivo indicado tras recorrer la escena durante 200 pasos\n")
                        print("Ejecute de nuevo el programa y pruebe con un objetivo distinto\n")
                        exit()

            # Call ExecOgamus to execute the action over the objective
            execute = ExecOgamus(controller, problem,
                                 objective_list[iteration], iteration)

            # Save facts found from OGAMUS into problems folder
            shutil.copyfile("OGAMUS/Plan/PDDL/facts.pddl",
                            f"pddl/problems/problem{iteration}.pddl")

            # Update agent position in for next OGAMUS execution
            event = controller.step("Pass")
            agent_pos = event.metadata["agent"]["position"]
            agent_rot = event.metadata["agent"]["rotation"]
            agent_hor = event.metadata["agent"]["cameraHorizon"]

            # Update iteration count
            iteration += 1