#!/usr/bin/env python3
"""
AI Rescue USB - Main Bootloader
Entry point for the entire system
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.system import AISystem
from detection.hardware import HardwareDetector
from ui.tty_interface import TTYInterface


class Bootloader:
    """Main boot sequence orchestrator"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.system = None
        self.detector = None
        self.ui = None
        
    def setup_logging(self):
        """Configure logging for the system"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler('/var/log/ai-rescue/boot.log'),
                logging.StreamHandler()
            ]
        )
        
    def initialize_system(self):
        """Initialize core AI system"""
        self.logger.info("Initializing AI Core...")
        self.system = AISystem()
        
        if not self.system.initialize():
            self.logger.error("Failed to initialize AI system")
            return False
            
        self.logger.info("AI Core ready")
        return True
        
    def detect_hardware(self):
        """Detect all hardware components"""
        self.logger.info("Detecting hardware...")
        self.detector = HardwareDetector()
        hardware_info = self.detector.scan_all()
        
        self.logger.info(f"Found {len(hardware_info)} devices")
        return hardware_info
        
    def start_interface(self):
        """Start the user interface"""
        self.logger.info("Starting user interface...")
        self.ui = TTYInterface(self.system, self.detector)
        return self.ui
        
    def run(self):
        """Main boot sequence"""
        try:
            print("=" * 60)
            print("AI RESCUE USB - Universal Computer Technician")
            print("=" * 60)
            print()
            
            self.setup_logging()
            self.logger.info("Boot sequence started")
            
            # Step 1: Initialize AI
            if not self.initialize_system():
                self.logger.error("System initialization failed")
                sys.exit(1)
                
            # Step 2: Detect hardware
            hardware = self.detect_hardware()
            self.logger.info("Hardware detection complete")
            
            # Step 3: Start UI
            self.ui = self.start_interface()
            if not self.ui:
                self.logger.error("UI failed to start")
                sys.exit(1)
                
            self.logger.info("System ready - entering main loop")
            print()
            
            # Step 4: Enter main loop
            self.ui.run()
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested by user")
            self.shutdown()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            sys.exit(1)
            
    def shutdown(self):
        """Clean shutdown sequence"""
        self.logger.info("Shutting down system...")
        
        if self.ui:
            self.ui.shutdown()
            
        if self.system:
            self.system.shutdown()
            
        self.logger.info("Shutdown complete")


def main():
    """Main entry point"""
    bootloader = Bootloader()
    bootloader.run()


if __name__ == "__main__":
    main()
