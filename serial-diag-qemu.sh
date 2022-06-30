# QEMU executable locations

# QEMU=/opt/xpack-qemu-arm-2.8.0-9/bin/qemu-system-gnuarmeclipse
# QEMU=~/xpack-qemu-arm-2.8.0-9/bin/qemu-system-gnuarmeclipse
QEMU=~/Work/qemu-arm-2.8.0-9/linux-x64/install/qemu-arm/bin/qemu-system-gnuarmeclipse
# QEMU=./xpack-qemu-arm-2.8.0-9/bin/qemu-system-gnuarmeclipse

$QEMU --verbose --board Feabhas-WMS -d unimp,guest_errors --semihosting-config enable=on,target=native \
  -serial telnet:localhost:8888,server,nodelay \
  --image build/debug/Application.elf \
  -serial tcp::7777,server,nodelay \
  -nographic
 