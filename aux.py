# Auxiliary functions
# Imports
from PIL import Image as im
import os
import shutil

def printAgentStatus(event):
    '''Shows general info and agent status'''
    print("-----------------------------------------------")
    print(f'sceneName: {event.metadata["sceneName"]}')
    print(f'lastAction: {event.metadata["lastAction"]}')
    print(f'agent cameraHorizon: {event.metadata["agent"]["cameraHorizon"]}')
    print(f'agent isStanding: {event.metadata["agent"]["isStanding"]}')
    print(f'agent position: {event.metadata["agent"]["position"]}')
    print(f'agent rotation: {event.metadata["agent"]["rotation"]}')
    print("-----------------------------------------------\n")

def isObjectOnScene(event, object):
    '''Check if an object is on the scene. Useful for OGAMUS'''
    print("-----------------------------------------------")
    for obj in event.metadata["objects"]:
        if obj["name"].lower().find(object) != -1:
            print(f'{object} existe en la escena')
    print("-----------------------------------------------\n")


def is_float(string):
    try:
        float(string)
        return True
    except:
        return False

def is_dictionary(property):
    return isinstance(property, dict)


def property_changed(oldValue, newValue):
    if newValue == oldValue:
        return False

    # this property was changed
    if is_float(oldValue) and is_float(newValue):
        # this property is a number, handle changes considering float tolerances
        floats_differ = abs(float(oldValue) - float(newValue)) > 1e-2
        return floats_differ
    else:
        return True

    #property_is_dictionary = isinstance(oldValue, dict)
    #if property_is_dictionary:


def get_changed_properties(old, new, path = None) -> list:
    properties_to_be_ignored = ["axisAlignedBoundingBox", "objectOrientedBoundingBox"]

    changes = []
    if path is None:
        path = []

    for key, value in old.items():
        if key in properties_to_be_ignored:
            # skip those properties, do not ever mark them as changed
            continue

        current_path = list.copy(path)
        current_path.append(key)
        oldValue = old[key]
        newValue = new[key]
        if is_dictionary(value):
            sub_property_changes = get_changed_properties(oldValue, newValue, current_path)
            if len(sub_property_changes) > 0:
                changes.append(sub_property_changes)
        else:
            if property_changed(oldValue, newValue):
                changes.append(current_path)

    return changes



def printObjectStatus(event, object):
    '''Shows full state of an object'''
    print("-----------------------------------------------")
    for obj in event.metadata["objects"]:
        if obj['objectId'] == object['objectId']:
            changes = get_changed_properties(object, obj)
            for changedPath in changes:
                for path in changedPath:
                    oldProperty = object
                    newProperty = obj
                    if isinstance(path, list):
                        # navigate the nested dictionaries
                        for key in path:
                            oldProperty = oldProperty[key]
                            newProperty = newProperty[key]
                        path = ".".join(path)
                    else:
                        # path is an immediate property
                        oldProperty = oldProperty[path]
                        newProperty = newProperty[path]
                    print(f" # '{path}' changed '{oldProperty}' ----> '{newProperty}'")

            break
    print("-----------------------------------------------\n")

def printLastActionStatus(event):
    '''Shows info of the last action executed'''
    print("-----------------------------------------------")
    print(f'lastAction: {event.metadata["lastAction"]}')
    print(f'lastActionSuccess: {event.metadata["lastActionSuccess"]}')
    if event.metadata["errorMessage"]:
        print(f'Error: {event.metadata["errorMessage"]}')
    print("-----------------------------------------------\n")

def extractActionImage(event, name):
    '''Extracts an image using event'''
    data = im.fromarray(event.frame)
    data.save("./images/" + name + ".png")

def createCamera(controller):
    '''Creates a camera and calls extractCameraImage() to save an image'''
    event = controller.step("Done")
    center = event.metadata["sceneBounds"]["center"]
    center["y"] = event.metadata["sceneBounds"]["cornerPoints"][0][1]
    camera_loc = center

    event = controller.step(
        action="AddThirdPartyCamera",
        position=camera_loc,
        rotation=dict(x=90, y=0, z=0),
        fieldOfView=110
    )
    extractCameraImage(event.third_party_camera_frames[0], 'scene')

def extractCameraImage(nparray, name):
    '''Extracts an image using a nparray'''

    data = im.fromarray(nparray)
    data.save("./images/" + name + ".png")

def ensureDirectoriesExist():
    dirs = ["./pddl/problems/", "./pddl/outputs/", "./images/", "./Results/"]
    for dir in dirs:
        if not os.path.exists(dir):
            os.makedirs(dir)

def removeResultFolders():
    '''Cleans result folders mentioned below'''
    dirs = ["./pddl/problems/", "./pddl/outputs/", "./images/", "./Results/"]
    
    for dir in dirs:
        for filename in os.listdir(dir):
            file_path = os.path.join(dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))




