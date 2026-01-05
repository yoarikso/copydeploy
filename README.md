# copydeploy.py

copydeploy.py - Copy folder contents from source to destination.
Supports include/exclude file filtering, dryrun mode, and sync mode.

## Usage

```bash
python3 copydeploy.py --help
```

### Options

- --dryrun: will not actually sync the files, but will show (output to the console) what would be copied.
- --sync: will actually sync the files. If not provided, it will only copy overwrite the destination folder with the source folder's content.
- --source: the source folder to copy from.
- --destination: the destination folder to copy to.
- --exclude: the exclude file to use.
- --include: the include file to use.

## the include file

The include file is a .txt file that lists a list of files and folders that should be copied.

```txt
/bin/* - This will copy overwrite all files and folders in the /bin folder.
file1.jpg - This will copy overwrite the file file1.jpg.
file2.txt - This will copy overwrite the file file2.txt.
file3.png - This will copy overwrite the file file3.png.
```

## the exclude file

The exclude file is a .txt file that lists a list of files and folders that should not be copied.

```txt
/bin/* - This will exclude all files and folders in the /bin folder.
file1.jpg - This will exclude the file file1.jpg.
file2.txt - This will exclude the file file2.txt.
file3.png - This will exclude the file file3.png.
```
