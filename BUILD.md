# building executables

here's how to build a standalone .exe or binary ig.

## what you need

- python 3.10+
- all dependencies: `pip install -r requirements.txt`
- pyinstaller: `pip install pyinstaller`
- yt-dlp: `pip install yt-dlp`

## build it

**windows:**
```bash
build_windows.bat
# exe will be in dist/scd.exe
```

**linux:**
```bash
chmod +x build_linux.sh
./build_linux.sh
# binary will be in dist/scd
```

**manual:**
```bash
pip install pyinstaller
pyinstaller scd.spec
```

## test it

```bash
# windows
dist\scd.exe --help

# linux
./dist/scd --help
```

## important stuff

**yt-dlp is separate** - the executable doesn't include yt-dlp. users need to install it:
```bash
pip install yt-dlp
```

why? because yt-dlp updates all the time to fix download issues. keeping it separate means people can update it without rebuilding the whole thing.

**file size** - expect ~20-30mb because of bundled python libraries

**cross-platform** - you can't build windows exe on linux or vice versa. build on the target platform.

## problems

**"module not found"**
```bash
pip install -r requirements.txt --force-reinstall
```

**"yt-dlp not found" when running**
```bash
pip install yt-dlp
```

**build fails**
```bash
rm -rf build dist __pycache__
pyinstaller --clean scd.spec
```

**exe is huge**
- that's normal, it's bundling python + libraries
- already using upx compression

## distributing

if you share the executable:
1. mention yt-dlp needs to be installed separately
2. test on a clean system first
3. include the readme

that's it
