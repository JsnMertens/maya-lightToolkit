#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Install jmLightToolkit. """

import maya.cmds as cmds
import maya.mel as mel
import os
import sys
import logging

logger = logging.getLogger(__name__)


def onMayaDroppedPythonFile(*args, **kwargs):
    """ Dragging and dropping one into the scene automatically executes it. """
    # Get icon
    icon_path = os.path.join(os.path.dirname(__file__), 'src', 'resources', 'icons', 'logo_jm.png')
    icon_path = os.path.normpath(icon_path)

    # Check if icon exist
    if not os.path.exists(icon_path):
        logger.error("Cannot find %s" % icon_path)
        return None

    # Check PYTHONPATH
    try:
        import jmLightToolkit
    except ImportError:
        logger.error("'jmLightToolkit' not found in PYTHON_PATH")
        return None

    # Create Shelf
    command  = "import jmLightToolkit;"
    command += "jmLightToolkit.main();"
    shelf = mel.eval('$gShelfTopLevel=$gShelfTopLevel')
    parent = cmds.tabLayout(shelf, query=True, selectTab=True)

    cmds.shelfButton(
        command=command,
        annotation='jmLightToolkit',
        sourceType='Python',
        image=icon_path,
        image1=icon_path,
        parent=parent )
