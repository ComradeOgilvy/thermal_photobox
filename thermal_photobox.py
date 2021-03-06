#!/usr/bin/env python3

import argparse
import os
import configparser
import logging
import time
import subprocess
import sys
from datetime import datetime, timedelta

# Note that the folowing packages are Raspberry Pi specific
from picamera import PiCamera
from picamera import Color

import RPi.GPIO as GPIO

"""
GPIO Initialization
"""


def _initialize_GPIO(GPIO_config):
    logging.info("Initialize GPIO")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    # Green LED
    GPIO.setup(GPIO_config["green_led_pin"], GPIO.OUT, initial=GPIO.HIGH)
    # Red LED
    GPIO.setup(GPIO_config["red_led_pin"], GPIO.OUT, initial=GPIO.LOW)
    # Arcade Button
    GPIO.setup(GPIO_config["button_pin"], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


"""
Camera Initialization
"""


def _initialize_camera(config_camera):
    logging.info("Initialize Camera")
    # Parse configuration options
    resolution_height = config_camera["resolution_height"]
    resolution_width = config_camera["resolution_width"]
    annotate_text_size = config_camera["annotate_text_size"]
    annotate_text = config_camera["annotate_text"]
    annotate_foreground = config_camera["annotate_foreground"]
    annotate_background = config_camera["annotate_background"]

    camera = PiCamera()
    logging.debug("Image Resolution: Height=[%s]; Width=[%s]" % (
        resolution_height, resolution_width))
    camera.resolution = (resolution_height, resolution_width)
    # turn camera to black and white
    camera.color_effects = (128, 128)
    camera.contrast = config_camera["contrast"]
    camera.brightness = config_camera["brightness"]
    camera.exposure_mode = 'auto'

    if config_camera["annotate"]:
        logging.debug("Set annotate text size to [%s]" % (annotate_text_size))
        camera.annotate_text_size = annotate_text_size
        camera.annotate_foreground = Color(annotate_foreground)
        camera.annotate_background = Color(annotate_background)
        text = ' ' + annotate_text + ' '
        logging.debug("Annotate text is [%s]" % (text))
        camera.annotate_text = text

    logging.info("Start Camera Preview")
    #camera.start_preview()

    return camera


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


def _launch_command(command: list):
    try:
        logging.debug('Start subprocess '+'"' +
                      ' '.join(map(str, command))+'"')
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        logging.debug('Finished subprocess '+'"' +
                      ' '.join(map(str, command))+'"')
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
            % (e.output, e.returncode)
        )
        return None


def _print_image(image_path):
    print_image_command = [
        "lp",
        "-o",
        "-fit-to-page",
        image_path,
        "-d",
        "Zijiang-ZJ-58"
    ]
    logging.info("Print image [%s]", image_path)
    _launch_command(print_image_command)

    return


def _wait_for_printer():
    logging.info("Wait for printer to finish printing")
    printer_status_command = [
        "lpstat",
        "-p",
        "Zijiang-ZJ-58"
    ]
    while True:
        if "Zijiang-ZJ-58 is idle" in _launch_command(printer_status_command):
            break
        else:
            time.sleep(1)
            continue


def _take_image(config_output, config_camera, camera):
    # Increment image counter if not temporary
    if not config_output["temporary"]:
        config_output["image_counter"] += 1
        update_image_counter(config_output["image_counter"])
        logging.debug("Image counter is [%s]", config_output["image_counter"])

    output_path = config_output["output_path"]
    image_name = config_output["image_name"]
    image_counter = config_output["image_counter"]
    image_path = output_path + image_name + '_' + str(image_counter) + '.jpeg'
    # Save current image path into config
    config_output["current_image_path"] = image_path
    logging.debug("Image Path is [%s]", image_path)

    logging.info("Capture Picture, Image_path is [%s]" % image_path)
    camera.capture(image_path)

    return config_output


def _red_led_blinking(red_led_pin):
    logging.info("Red LED blinking")
    for x in range(3):
        time.sleep(0.5)
        GPIO.output(red_led_pin, GPIO.LOW)
        time.sleep(0.5)
        GPIO.output(red_led_pin, GPIO.HIGH)


def _red_led_flashing(red_led_pin):
    logging.info("Red LED flashing")
    for x in range(3):
        time.sleep(0.2)
        GPIO.output(red_led_pin, GPIO.LOW)
        time.sleep(0.2)
        GPIO.output(red_led_pin, GPIO.HIGH)


def update_image_counter(image_counter):
    with open('counter', 'w') as counter:    # save
        counter.write(str(image_counter))


"""
Main Logic
- handle button input
- if button pressed:
    - deactivate green led
    - activate red led
    - red led flashing
    - red led blinking
    - capture picture
    - print picture
    - deactivate red led
    - activate green led
"""


def _main(config, camera):
    green_led_pin = config["GPIO"]["green_led_pin"]
    red_led_pin = config["GPIO"]["red_led_pin"]
    button_pin = config["GPIO"]["button_pin"]

    logging.info("Starting Main Loop")
    while(True):
        if GPIO.input(button_pin) == GPIO.HIGH:
            camera.start_preview()
            # Switch LEDs
            logging.info("Button pressed! Switching LEDs")
            GPIO.output(red_led_pin, GPIO.HIGH)
            GPIO.output(green_led_pin, GPIO.LOW)

            # Red LED blinking and flashing for visual feedback
            _red_led_blinking(red_led_pin)
            _red_led_flashing(red_led_pin)
            
            GPIO.output(red_led_pin, GPIO.LOW)
            # Start Capturing the image
            config["output"] = _take_image(
                config["output"], config["camera"], camera)
            _print_image(config["output"]["current_image_path"])
            camera.stop_preview()
            GPIO.output(red_led_pin, GPIO.HIGH)
            _wait_for_printer()

            # Switch LEDs back
            logging.debug("Switching LEDs back")
            GPIO.output(red_led_pin, GPIO.LOW)
            GPIO.output(green_led_pin, GPIO.HIGH)
        time.sleep(0.05)
    return 0


"""
Main Initialization
"""


def main(arguments):
    try:
        t0 = time.monotonic()
        exit_status = 2
        """
        Initialize configuration parser
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
        logging.getLogger().setLevel(logging.INFO)

        """
        Parse the remaining configuration options into a configuration dictionary
        """
        config = {}
        config["output"] = {}
        config["camera"] = {}
        config["GPIO"] = {}
        try:
            config["output"]["output_path"] = cfg.get("output", "output_path")
            logging.info("Output-path: [%s]", config["output"]["output_path"])
            config["output"]["temporary"] = cfg.getboolean(
                "output", "temporary")
            if config["output"]["temporary"]:
                logging.info("Images are saved only temporary")
            else:
                logging.info("Images are saved permanently")
            config["output"]["image_name"] = cfg.get("output", "image_name")
            logging.info(
                "Base image name is [%s]", config["output"]["image_name"])
            config["camera"]["annotate"] = cfg.getboolean("camera", "annotate")
            if config["camera"]["annotate"]:
                logging.info("Annotation is enabled")
            else:
                logging.info("Annotation is disabled")
            config["camera"]["annotate_text"] = cfg.get(
                "camera", "annotate_text")
            logging.info("Annotate text is [%s]",
                         config["camera"]["annotate_text"])
            config["camera"]["annotate_text_size"] = cfg.getint(
                "camera", "annotate_text_size")
            logging.info(
                "Annotate text size is [%s]", config["camera"]["annotate_text_size"])
            config["camera"]["annotate_foreground"] = cfg.get(
                "camera", "annotate_foreground")
            logging.info(
                "Annotate foreground color is [%s]", config["camera"]["annotate_foreground"])
            config["camera"]["annotate_background"] = cfg.get(
                "camera", "annotate_background")
            logging.info(
                "Annotate background color is [%s]", config["camera"]["annotate_background"])
            config["camera"]["resolution_height"] = cfg.getint(
                "camera", "resolution_height")
            logging.info(
                "Image resolution height is [%s]", config["camera"]["resolution_height"])
            config["camera"]["resolution_width"] = cfg.getint(
                "camera", "resolution_width")
            logging.info(
                "Image resolution width is [%s]", config["camera"]["resolution_width"])
            config["camera"]["contrast"] = cfg.getint("camera", "contrast")
            logging.info(
                "Camera contrast is [%s]", config["camera"]["contrast"])
            config["camera"]["brightness"] = cfg.getint("camera", "brightness")
            logging.info(
                "Camera brightness is [%s]", config["camera"]["brightness"])
            config["GPIO"]["button_pin"] = cfg.getint("GPIO", "button_pin")
            logging.info("Button GPIO is [%s]", config["GPIO"]["button_pin"])
            config["GPIO"]["green_led_pin"] = cfg.getint(
                "GPIO", "green_led_pin")
            logging.info("Green LED GPIO is [%s]",
                         config["GPIO"]["green_led_pin"])
            config["GPIO"]["red_led_pin"] = cfg.getint("GPIO", "red_led_pin")
            logging.info("Red LED GPIO is [%s]", config["GPIO"]["red_led_pin"])
        except(configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.exception(
                "Could not parse configuration options. Error: [%s]", str(e))
            raise

        # image counter is used for the image file name(s)
        logging.info("Read image counter")
        with open('counter', 'r') as counter:
            config["output"]["image_counter"] = int(counter.read())
            logging.info("Image counter is [%s]",
                         config["output"]["image_counter"])

        """
        Start counting the time and start application
        """
        t0 = time.monotonic()
        logging.critical(
            "=== START OF APPLICATION AT %s ===",
            datetime.utcnow().isoformat()
        )

        try:
            # Initialize GPIOs
            _initialize_GPIO(config["GPIO"])
            # Initialize Camera
            camera = _initialize_camera(config["camera"])

            """
            start main logic
            """
            exit_status = _main(config, camera)
        except Exception as e:
            exit_status = 3
            logging.exception("Execution failed: %s", str(e))
            raise

    finally:
        # GPIO Cleanup
        logging.info("GPIO Cleanup")
        GPIO.cleanup()
        # Camera Cleanup
        logging.info("Camera Cleanup")
        camera.stop_preview()
        camera.close()
        # Calculate Duration and exit the application
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
        description="Thermal Photobox for low budget instant photos"
    )
    parser.add_argument(
        "-c", "--config",
        default='./config.ini',
        type=argparse.FileType("r"),
        help="Configuration file"
    )
    args = parser.parse_args()
    main(args)
