#!/usr/bin/env python3
"""MegaTree - Ultimate Device Tree Generator from Stock ROM Dumps"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from megatree.__main__ import main
sys.exit(main())
