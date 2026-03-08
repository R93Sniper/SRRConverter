# SRRConverter V2
Welcome to the SRRConverter repo.
This is a python script used to interact with the newer remastered soul reaver games.

Current functionality:
|Function|Description|
|---|---|
|`--help`|Displays full info on commands|
|`version`|Prints version information|
|`hash <string>`|Return a hash of the specified string|
|`extract manifest -i <hash.manifest> -b <bigfile> [-o <outpath>]`|Extracts all the files found in a specified manifest file|
|`extract file -i <filename/hash> -b <bigfile> [-o <outpath] `|Extracts a file from the BigFile using a name or hash as the target|

> ***Note*** The commands have more features. Each verb has more info with the -h flag

As of the current time anything is subject to change.