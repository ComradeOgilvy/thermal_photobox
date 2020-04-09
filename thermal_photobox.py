#!/usr/bin/env python3

import argparse
import os
import configparser
import logging
import time
import subprocess
import sys
from datetime import datetime, timedelta

#from picamera import PiCamera
#from picamera import Color

"""
Helper Function to call an bash command
- calls a shell command and returns the output (utf8 encoded)
- stderr is piped to stdout
- stdin is forbidden
- debug:
  - print start of command
  - print end of command
  - print output of command
"""
def _launch_command(command:list):
    """
    Run the command given. The command has to be simple, not containing any 
    bash elements.

    Raise a ValueError if the command asked is not found.
    :param command: the different parts of the command have to be given as 
    different elements of a list:

    example: "ls -l file.txt" has to be given as: ["ls", "-l", "file.txt"]
    :return:    The output of the command decoded with UTF-8, 
                None if an issue occurred
    """
    try:
        logging.debug('Start subprocess '+'"'+ ' '.join(map(str,command))+'"')
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        logging.debug('Finished subprocess '+'"'+ 
            ' '.join(map(str,command))+'"')
        output = process.stdout.read().decode('UTF-8').rstrip()
        logging.debug('[output] %s', output)
        return output
    except FileNotFoundError as fe:
        logging.exception(
            "The command '{}' could not be found.".format(fe.filename)
        )
        return None
    except subprocess.CalledProcessError as e:
        logging.exception(
            "The subprocess failed with: output = %s, error code = %s" 
            %(e.output, e.returncode)
        )
        return None

def _print_image(tmp_image):
    print_image_command = [
        "lp",
        "-o",
        "-fit-to-page",
        tmp_image
    ]
    logging.info("Print image [%s]", tmp_image)
    _launch_command(print_image_command)
    return

def _take_image(config_output, config_camera, image_counter):
    resolution_height = config_camera["resolution_height"]
    resolution_width = config_camera["resolution_width"]
    annotate_text_size = config_camera["annotate_text_size"]
    annotate_text = config_camera["annotate_text"]
    annotate_foreground = config_camera["annotate_foreground"]
    annotate_background = config_camera["annotate_background"]
    output_path = config_output["output_path"]
    image_name = config_output["image_name"]
    image_path = output_path + image_name + '_' + image_counter + '.jpeg'

    camera = PiCamera()
    logging.debug("Image Resolution: Height=[%s]; Width=[%s]" %(resolution_height,resolution_width))
    camera.resolution = (resolution_height, resolution_width)
    logging.debug("Start Camera Preview")
    camera.start_preview()
    logging.debug("Set annotate text size to [%s]" %(annotate_text_size))
    camera.annotate_size = annotate_text_size
    camera.annotate_foreground = Color(annotate_foreground)
    camera.annotate_background = Color(annotate_background)
    text = ' ' + annotate_text + ' '
    logging.debug("Annotate text is [%s]" %(text))
    camera.annotate_text = text
    # it is important to sleep for at least two seconds before capturing an image, 
    # because this gives the cameras sensor time to sense the light levels
    logging.debug("Sleeping for 4 seconds")
    time.sleep(4)
    logging.info("Image_path is [%s]" %image_path)
    camera.capture(image_path)
    logging.debug("End Camera Preview")
    camera.stop_preview()
    return

"""
Main Logic
- describe main logic here
"""
def _main(config):
    image_counter = 0

    logging.info("Starting Main Loop")
    while(True):
        # ---
        #image_path = output_path + image + '_' + image_counter + '.jpeg'
        #_take_image(image_path, config["annotate_text"], config["annotate_text_size"], config[""])
        #_print_image(image_path)
        #if config["temporary"]:
        #    image_counter += 1
        if False:
            print("hello")
    return 0

"""
Main Initialization
"""
def main(arguments):
    try:
        t0 = time.monotonic()
        exit_status=2
        """
        Initialize configuration
        """
        cfg = configparser.ConfigParser()
        try:
            with args.config as f:
                cfg.read_file(f)
        except IOError as e:
            exit_status = 1
            logging.exception(
                "Cannot open Configuration File: [%s]", str(e)
            )
            raise
        
        """ 
        Initialize the logger
        """
        # try to get log path from config file
        try:
            log_file = cfg.get("logging", "log_file")
        except (configparser.NoSectionError, configparser.NoOptionError):
            log_file = os.getcwd() + '/thermal_photobox.log'
        # Check if we have write access to the log file
        # Otherwise use current working directory
        if not (os.access(log_file, os.W_OK)):
            logging.error(
                "No write access to %s, put log file into current working directory",
                log_file
                )
            log_file = os.getcwd()+'/thermal_photobox.log'
        logging_handler = logging.FileHandler(
            log_file,
            mode="w",
        )
        logging_formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        logging_handler.setFormatter(logging_formatter)
        logging.getLogger().addHandler(logging_handler)
        logging.getLogger().setLevel(logging.DEBUG)

        """
        Parse the remaining configuration options into a configuration dictionary
        """
        config = {}
        config["output"] = {}
        config["camera"] = {}
        config["button"] = {}
        try:
            config["output"]["output_path"] = cfg.get("output","output_path")
            logging.info("Output-path: [%s]", config["output"]["output_path"])
            config["output"]["temporary"] = cfg.get("output", "temporary")
            if config["output"]["temporary"]:
                logging.info("Image are saved only temporary")
            else:
                logging.info("images are saved permanently")
            config["output"]["image_name"] = cfg.get("output","image_name")
            logging.info("Base image name is [%s]", config["output"]["image_name"])
            config["camera"]["annotate_text"] = cfg.get("camera", "annotate_text")
            logging.info("Annotate text is [%s]", config["camera"]["annotate_text"])
            config["camera"]["annotate_foreground"] = cfg.get("camera", "annotate_foreground")
            logging.info("Annotate foreground color is [%s]", config["camera"]["annotate_foreground"])
            config["camera"]["annotate_background"] = cfg.get("camera", "annotate_background")
            logging.info("Annotate background color is [%s]", config["camera"]["annotate_background"])
            config["camera"]["resolution_height"] = cfg.get("camera", "resolution_height")
            logging.info("Resoltion height is [%s]", config["camera"]["resolution_height"])
            config["camera"]["resolution_width"] = cfg.get("camera", "resolution_width")
            logging.info("Resolution width is [%s]", config["camera"]["resolution_width"])
            config["button"]["button_pin"] = cfg.get("button","button_pin")
        except(configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.exception("Could not parse configuration options. Error: [%s]", str(e))
            raise

        """
        Start counting the time and start application
        """
        t0 = time.monotonic()
        logging.critical(
                "=== START OF APPLICATION AT %s ===",
                datetime.utcnow().isoformat()
            )
        try:
            """
            start main logic
            """
            exit_status = _main(config)
        except Exception as e:
            exit_status = 3
            logging.exception("Execution failed: %s", str(e))
            raise

    finally:
        """
        Calculate Duration and exit the application
        """
        t1 = time.monotonic()
        duration = t1 - t0
        logging.critical(
            "=== END OF APPLICATION AT %s (%s) ===",
            datetime.utcnow().isoformat(),
            timedelta(seconds=duration),
        )
        sys.exit(exit_status)

"""
Load the CLI parameters
"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Lorem ipsum dolor sit amet"
    )
    parser.add_argument(
        "-c", "--config",
        default='./config.ini',
        type=argparse.FileType("r"),
        help="Configuration file"
    )
    args = parser.parse_args()
    main(args)
