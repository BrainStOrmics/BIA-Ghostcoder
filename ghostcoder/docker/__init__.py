import os
from pathlib import Path
import docker
import json
import docker.errors
from ..config import *


# DOCKER_IMAGES = ['python:3.9-slim', 'r-base:4.2.3']


def load_docker_profiles():
    if len(docker_config.DOCKER_PROFILES_DIR) > 0:
        profile_dir = docker_config.DOCKER_PROFILES_DIR
    else:
        profile_dir = os.path.dirname(os.path.abspath(__file__))
    default_profile_path = os.path.join(profile_dir,docker_config.DEFAULT_DOCKER_PROFILE)
    new_profile_path = os.path.join(profile_dir,docker_config.NEW_DOCKER_PROFILE)
    if os.path.exists(new_profile_path):
        profile_path = new_profile_path
    else:
        profile_path = default_profile_path
    with open(profile_path, 'r', encoding = 'utf-8') as f:
        profiles = json.load(f)
    return profiles

def check_docker_exists(
        name:str,
        tag:str,
        ):
    target_tags = name+':'+tag
    client = docker.from_env()
    images = client.images.list()
    for img in images:
        if img.tags == target_tags:
            return True
    return False

def get_docker_status():
    docker_status_str = "Loaded dockers are:\n"
    docker_profiles = load_docker_profiles()
    docker_images = docker.from_env().images.list()
    all_loaded_tags = []
    for img in docker_images:
        all_loaded_tags.append(img.tags[0]) 
    for profile in docker_profiles['Docker images']:
        profile_tags = profile['name']+':'+profile['tag']
        profile_str = "docker name: " + profile_tags + "\n"
        profile_str += "docker description: " + profile['description'] + "\n"
        profile_str += "supported language: " + profile['languages'] + "\n"
        profile_str += "pre-installed packages: " + profile['packages'] + "\n"
        if profile_tags in all_loaded_tags:
            docker_status_str += profile_str
    return docker_status_str



def add_docker_image_profile(
        name:str,
        tag:str,
        description:str,
        language: str,
        packages: str,
        verbose = False,
    ):
    # Load docker profiles 
    docker_profiles = load_docker_profiles()
    
    # Check if profile existed 
    if check_docker_exists(name = name, tag = tag):
        return 

    # Build new profile 
    try:
        new_profile = {
            "name": name, # docker image id, from docker env, or docker hub
            "tag": tag, # docker image tag
            "description":description, # description of this docker
            "language": language, # coding language(s) fits in this docker
            "packages":packages, # pre-installed packages 
            }
    except:
        raise ValueError("There is illegitimate definitions in this new docker profile.")
    
    # Update docker profile
    docker_profiles['Docker images'].append(new_profile)
    if verbose:
        print("New docker profile added.")

    # Write new profiles
    new_profile_path = os.path.join(docker_config.DOCKER_PROFILES_DIR,docker_config.NEW_DOCKER_PROFILE)
    with open(new_profile_path, 'w') as f:
        json.dump(docker_profiles, f, indent=2)
    if verbose:
        print("New docker profile written.")    


def pull_docker_images(
        name:str, 
        tag:str,
        verbose = False,
        ):
    client = docker.from_env()
    docker_tags = name+':'+tag
    try:
        client.images.pull(docker_tags)
        if verbose:
            print(f"Successfully pulled docker image: {docker_tags}")
        return True
    except docker.errors.APIError as e:
        if verbose:
            print(f"Failed to pull image {docker_tags} due to {e}")
        return False

