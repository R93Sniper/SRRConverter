"""This file was created for SRRConveter project
License: GPLv3
Author: R93 Sniper
Description: Batch Converter Class
    Ask the user what files to convert and we shall convert them. All files to convert must be in their respective subfolders of Input\
    SRM Files -> Input\SRM
    SRA Files -> Input\SRA
    SRL Files -> Input\SRL
    Textures -> Input\Textures
    Heirarchy Definitions -> Input\Definitions
"""

from pathlib import Path
import fbx
from Source.SRMToFBX import SrmToFBX
from Source.Hry import buildDefinitions

class BatchConverter:

    # ================================================================================================================
    # Here's a list of Exit Codes
    # 0 - Successfully exit
    # 1 - Manual Exit
    # 2 - Directory Not Found
    # 3 - File Not Found
    # 4 - Manager Failed
    # 5 - Could Not Create Output File
    # 6 - 
    # ================================================================================================================

    # Root Input and Output Folders
    INPUT_DIR = Path("Input")
    OUTPUT_DIR = Path("Output")

    def CreateOutputFile(self, FileName: str, OutputString: str):
        """
        Create Output File Function
        Print the output log as a file
        """

        with open(FileName, "w", encoding="utf-8") as file:
            file.write(OutputString)


    def ConvertTextures():
        """
        Convert Textures Function
        Use Pillow to Convert textures from Input/Textures to Output/{Filename}
        TODO 1: Actually implement this function
        TODO 2: Let people pick what image type they want to convert to
        """

        print("Stub Function!")

        #We're going to use Pillow for this. 


    def ConvertFileToFBX(self, GenerateLog: bool, FilesInDirectory: list[Path]):
        """
        Convert File To FBX Function
        Converts all SRM files in Input\SRM to FBX and Outputs them to Output\
        Generates a log if requested.
        """

        #Create an FBX Manager
        print("Attempting to create FBX Manager")
        OurFileManager = fbx.FbxManager.Create()
        if not OurFileManager:
            print("FBX Manager could not be created.")
            exit(4)
        else:
            print("Successfully created FBX Manager!")

        #Start Converting files
        for i in FilesInDirectory:
            print(f"\nAttempting to convert {i.name} to FBX")
            OutputScene, LogString = SrmToFBX(i,OurFileManager,GenerateLog)
            
            #Create output paths per item we're converting
            OutputFile = BatchConverter.OUTPUT_DIR / f"{i.stem}.fbx"
            LogOutput = str(OutputFile.with_suffix(".txt"))

            #Validate that our FBX Scenes were made. Log if they failed 
            if not OutputScene:
                print(f"Could not generate FBX for {i.name}! Logged Output")
                self.CreateOutputFile(LogOutput, LogString)
                continue

            #Create an Export Manager for us to actually create our FBX File
            ExportManager = fbx.FbxExporter.Create(OurFileManager, "")
            if not ExportManager.Initialize(str(OutputFile)):
                print(f"Could not Create Export Manager for {OutputFile}")
                continue

            #Tell the manager to export the file
            if ExportManager.Export(OutputScene):
                print(f"Successfully Exported {OutputFile}")
            else:
                print(f"Could not export {OutputFile}")
                self.CreateOutputFile(LogOutput, LogString)
            
            #If we wanted to generate a log, generate it
            if GenerateLog:
                self.CreateOutputFile(LogOutput, LogString)
                print(f"Created Log file for {i.name}")

            #Destroy our Export Manager instance once we've finished with it
            ExportManager.Destroy()

        #Clean up once we've finished with everything
        print("\nAll files converted, cleaning up FBX Manager.")
        OurFileManager.Destroy()


    def ConvertModelFiles(self):
        """
        Convert Model Files
        Start the Process to convert SRM files
        TODO 1:  Allow conversion of other file formats (ie smd/gltf)
        """

        ValidInput = False
        GenerateLog: bool
        
        #Check to see if our user wants to generate an output log
        print("Do you want a log to be generated?")
        while not ValidInput:
            Response = input()
            if Response.lower() in ("yes","y","true"):
                GenerateLog = True
                ValidInput = True
            elif Response.lower() in ("no","n","false"):
                GenerateLog = False
                ValidInput = True
            else:
                print("Invalid Response; Yes or No")

        print("Looking for SRM files in Input/SRM...")
        #Search for SRM directory without case sensitivity
        #This is a really weird way to ensure Linux users can operate. Why must you be difficult, Linux users?
        InputSubdir = next((SubPath for SubPath in BatchConverter.INPUT_DIR.iterdir() if SubPath.is_dir() and SubPath.name.lower() == "srm"), None)
        BatchConverter.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        #Check to ensure our input directory exists. If it doesn't, create it and exit
        if not InputSubdir.exists():
            InputSubdir.mkdir(parents=True, exist_ok=True)
            print("SRM Subdirectory does not exist. Creating it now. Put SRM files in directory")
            exit(2)
        
        #Check all the files in the SRM Directory. If we don't find any, exit
        FilesInDirectory = [f for f in InputSubdir.iterdir() if f.is_file() and f.suffix.lower() == ".srm"]
        if not FilesInDirectory:
            print("No SRM files in directory. Add some files and try again.")
            exit(3)
        else:
            print(f"Discovered {len(FilesInDirectory)} SRM file(s).")

        #TODO 1
        self.ConvertFileToFBX(GenerateLog,FilesInDirectory)

        #We're done!
        print("Complete.")
        exit(0)

        
    def BatchConvert(self):
        """
        Batch Convert Function
        Main App Function
        Given some user inputs, batch convert the files
        TODO 1: Implement conversion of SRA Files
        TODO 2: Implement conversion of SRL Files
        """

        ValidInput = False

        #Ask User what kind of filetype to convert
        while not ValidInput:
            print("Pick a filetype to convert:")
            FileTypeToConvert = input()

            #Convert files based on type
            if FileTypeToConvert == "1":
                print("Converting SRM Files")
                ValidInput = True
                self.ConvertModelFiles()
            elif FileTypeToConvert == "2":
                print("SRA Support Incomplete, Exiting") #TODO 1
                exit(1)
            elif FileTypeToConvert == "3":
                print("SRL Support Incomplete, Exiting") #TODO 2
                exit(1)
            elif FileTypeToConvert == "4":
                print("Building Heirarchy Definitions from Input/Definitions")
                ValidInput = True
                buildDefinitions()
            elif FileTypeToConvert == "5":
                print("Texture conversion not implemented, Exiting")
                exit(1)
            elif FileTypeToConvert == "6":
                print("Exiting")
                exit(1)
            else:
                print("Select from the following: \n1) Soul Reaver Model (SRM)\n2) Soul Reaver Animation (SRA)\n3) Soul Reaver Lines (SRL)\n4) Heirarchy Definitions\n5) Textures\n6) Exit")


if __name__ == "__main__":
    """
    Instantiation Function
    Starts the main function when run in Terminal.
    This is weird python shit, Don't ask me.
    """

    Converter = BatchConverter()
    Converter.BatchConvert()