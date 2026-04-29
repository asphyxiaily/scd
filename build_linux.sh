#!/bin/bash

echo "building scd for linux..."

if ! command -v pyinstaller &> /dev/null; then
    echo "pyinstaller not found. installing..."
    pip install pyinstaller
fi

rm -rf build dist

pyinstaller scd.spec

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ build successful!"
    echo "executable: dist/scd"
    echo ""
    echo "to test:"
    echo "  ./dist/scd --help"
else
    echo "✗ build failed"
    exit 1
fi
