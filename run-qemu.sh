#!/bin/bash
# QEMU Invocation
# see https://www.qemu.org/docs/master/system/invocation.html

TARGET=Application.elf

USAGE="Usage: $0 [qemu-options] [gdb] [serial] [elf-image]"

if [[ $1 = --help || $1 = -? || $1 = '-h' ]]; then
    echo "$USAGE" >&2
    exit 1
fi

QEMU_PATH="xpack-qemu-arm-2.8.0-9/bin/qemu-system-gnuarmeclipse"
QEMU_DIRS="/opt $HOME"

for dir in $QEMU_DIRS; do
    QEMU="$dir/$QEMU_PATH"
    [[ -x $QEMU ]] && break
    QEMU=
done

if [[ -z $QEMU ]]; then
    echo "Cannot find QEMU in standard locations: $QEMU_DIRS" >&2
    exit 1
fi

GDB=
SERIAL=
OPTIONS=

for arg; do
    case "$arg" in
        gdb)         GDB='-S -gdb tcp::1234' ;;
        serial)      SERIAL='-serial tcp::7777,server,nodelay' ;;
        *.ELF|*.elf) IMAGE="$arg" ;;
        -*)          OPTIONS="$OPTIONS $arg" ;;
        *)
            echo "Unrecognised command argument: $arg" >&2
            echo "$USAGE" >&2
            exit 1
            ;;
    esac
done

# supply default image

: ${IMAGE:=build/debug/$TARGET}


set -x
$QEMU --verbose --board Feabhas-WMS -d unimp,guest_errors --semihosting-config enable=on,target=native $OPTIONS $GDB $SERIAL --image $IMAGE
