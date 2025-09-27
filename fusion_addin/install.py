"""
Installation and setup utilities for PinmapGen Fusion add-in.
"""

import os
import shutil
import json


class AddInInstaller:
    """Handles installation of the PinmapGen Fusion add-in."""
    
    def __init__(self):
        """Initialize installer."""
        pass
    
    def get_fusion_addins_path(self):
        """Get the Fusion 360 add-ins directory path."""
        # Common Fusion add-in locations
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA')
            return os.path.join(
                appdata, 
                'Autodesk', 
                'Autodesk Fusion 360', 
                'API', 
                'AddIns'
            )
        else:  # macOS
            home = os.path.expanduser('~')
            return os.path.join(
                home, 
                'Library', 
                'Application Support', 
                'Autodesk', 
                'Autodesk Fusion 360', 
                'API', 
                'AddIns'
            )
    
    def install_addin(self, source_path: str) -> bool:
        """
        Install the add-in to Fusion 360.
        
        Args:
            source_path: Path to the add-in source directory
            
        Returns:
            True if installation successful
        """
        try:
            fusion_addins_path = self.get_fusion_addins_path()
            target_path = os.path.join(fusion_addins_path, 'PinmapGen')
            
            # Create directory if it doesn't exist
            os.makedirs(fusion_addins_path, exist_ok=True)
            
            # Copy add-in files
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            
            shutil.copytree(source_path, target_path)
            
            print(f"PinmapGen add-in installed to: {target_path}")
            print("\nNext steps:")
            print("1. Start Fusion 360")
            print("2. Go to Tools > ADD-INS")
            print("3. Find 'PinmapGen' in the list")
            print("4. Click 'Run' to activate")
            print("5. Optionally click 'Run on Startup' for auto-activation")
            
            return True
            
        except Exception as e:
            print(f"Installation failed: {str(e)}")
            return False
    
    def create_development_link(self, source_path: str) -> bool:
        """
        Create a development link for testing (symlink on supported systems).
        
        Args:
            source_path: Path to the add-in source directory
            
        Returns:
            True if link creation successful
        """
        try:
            fusion_addins_path = self.get_fusion_addins_path()
            target_path = os.path.join(fusion_addins_path, 'PinmapGen_Dev')
            
            # Create directory if it doesn't exist
            os.makedirs(fusion_addins_path, exist_ok=True)
            
            # Remove existing link/directory
            if os.path.exists(target_path):
                if os.path.islink(target_path):
                    os.unlink(target_path)
                else:
                    shutil.rmtree(target_path)
            
            # Try to create symlink (requires admin on Windows)
            try:
                os.symlink(source_path, target_path)
                print(f"Development link created: {target_path}")
                return True
            except OSError:
                # Fallback to copying for development
                shutil.copytree(source_path, target_path)
                print(f"Development copy created: {target_path}")
                print("Note: Using copy instead of symlink. "
                      "You'll need to reinstall after changes.")
                return True
                
        except Exception as e:
            print(f"Development link creation failed: {str(e)}")
            return False


if __name__ == "__main__":
    """Install or set up development environment for PinmapGen add-in."""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Install PinmapGen Fusion 360 Add-in"
    )
    parser.add_argument(
        '--dev', 
        action='store_true',
        help='Create development link instead of installing'
    )
    parser.add_argument(
        '--source',
        default=os.path.dirname(__file__),
        help='Source directory path (default: current directory)'
    )
    
    args = parser.parse_args()
    
    installer = AddInInstaller()
    
    if args.dev:
        success = installer.create_development_link(args.source)
        if success:
            print("\n🔧 Development setup complete!")
            print("The add-in will update automatically as you modify the code.")
    else:
        success = installer.install_addin(args.source)
        if success:
            print("\n✅ Installation complete!")
            print("The add-in is ready to use in Fusion 360.")
    
    if not success:
        print("\n❌ Setup failed. Please check the error messages above.")
        exit(1)