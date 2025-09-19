#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BIA-Ghostcoder Logging Utilities
# Provides logging configuration and initialization functions for the BIA-Ghostcoder
# system. Enables consistent logging across all components with standardized formatting
# and output management for debugging and monitoring purposes.

import logging
import time

#######################################
# Initialize logging configuration for BIA-Ghostcoder system
# Globals:
#   None (configures global logging system)
# Arguments:
#   log_filename (str): Path to log file for output
# Returns:
#   None (configures logging system globally)
#######################################
def initial_log(log_filename: str = 'log.txt') -> None:
    """
    Initialize logging configuration for the BIA-Ghostcoder system.
    
    This function sets up a standardized logging configuration that provides
    consistent formatting and output management across all BIA-Ghostcoder components.
    It configures file-based logging with informative message formatting including
    timestamps, logger names, and severity levels.
    
    Args:
        log_filename (str, optional): Path to the log file where all log messages
                                    will be written. Defaults to 'log.txt' in the
                                    current working directory.
    
    Returns:
        None: This function configures the global logging system and doesn't
              return any values.
    
    Note:
        This function uses 'w' filemode which overwrites existing log files.
        Each run of the application will start with a fresh log file.
    """
    # Configure the global logging system with standardized settings
    logging.basicConfig(
        # Set logging level to INFO to capture important operational messages
        # This excludes DEBUG messages but includes INFO, WARNING, ERROR, and CRITICAL
        level=logging.INFO,
        
        # Define a comprehensive log message format with key information:
        # - %(name)s: Logger name (typically module name)
        # - %(levelname)s: Severity level (INFO, WARNING, ERROR, etc.)
        # - %(asctime)s: Timestamp when the log message was created
        # - %(message)s: The actual log message content
        format='[%(name)s-%(levelname)s]-[%(asctime)s] %(message)s',
        
        # Set timestamp format to hours:minutes:seconds for readability
        # This provides sufficient precision for most debugging scenarios
        datefmt='%H:%M:%S',
        
        # Specify the output file for all log messages
        # All components of BIA-Ghostcoder will write to this single log file
        filename=log_filename,
        
        # Use 'w' mode to overwrite existing log file on each run
        # This ensures a fresh log for each analysis session
        # TODO(developer): Consider 'a' mode for persistent logging across runs
        filemode='w'
    )

