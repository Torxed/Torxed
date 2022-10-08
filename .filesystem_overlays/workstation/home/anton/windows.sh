#!/bin/bash

sudo sysctl vm.nr_hugepages=4096

# https://wiki.archlinux.org/title/PCI_passthrough_via_OVMF#CPU_pinning
# lscpu -e --json

#       -device ich9-intel-hda,id=sound0,bus=pcie.0,addr=0x1b \
#               -device hda-micro,id=sound0-codec0,bus=sound0.0,cad=0,audiodev=hda \
#                       -audiodev pa,id=hda,server=unix:/tmp/pulse-socket,out.mixing-engine=off,out.buffer-length=512,timer-period=1000 \

# sudo cp ~/.config/pulse/cookie /root/.config/pulse/cookie
sudo taskset --cpu-list 8-11 qemu-system-x86_64 \
        -name "testmachine" \
        -pidfile /tmp/ourkvm_testmachine.pid \
        -cpu host,topoext,kvm=off,hv_relaxed,hv_spinlocks=0x1fff,hv_vapic,hv_time \
        -enable-kvm \
        -machine q35,accel=kvm \
        -device intel-iommu,device-iotlb=on,caching-mode=on \
        -device pcie-root-port,port=0xa,chassis=1,id=pci.1,bus=pcie.0,multifunction=on,addr=0x3 \
                -device qemu-xhci,p2=15,p3=15,id=usb,bus=pci.1,addr=0x0 \
        -device pcie-root-port,port=0xb,chassis=5,id=pci.5,bus=pcie.0,addr=0x4 \
        -device pcie-pci-bridge,id=pci.7,bus=pci.5,addr=0x0 \
        -device ivshmem-plain,id=shmem0,memdev=shmmem-shmem0,bus=pci.7,addr=0x1 \
        -device pcie-root-port,port=0xc,chassis=2,id=pci.2,bus=pcie.0,multifunction=on,addr=0x5 \
        -device virtio-serial-pci,id=virtio-serial0,bus=pci.2,addr=0x0 \
        -device pcie-root-port,port=0xd,chassis=6,id=pci.6,bus=pcie.0,addr=0x5.0x1 \
        -device virtio-mouse-pci,id=input0,bus=pci.6,addr=0x0 \
        -device pcie-root-port,port=0xe,chassis=8,id=pci.8,bus=pcie.0,multifunction=on,addr=0x6 \
        -device virtio-keyboard-pci,id=input1,bus=pci.8,addr=0x0 \
        -device pcie-root-port,port=0xf,chassis=9,id=pci.9,bus=pcie.0,addr=0x6.0x1 \
        -device bochs-display,id=video0,vgamem=16384k,bus=pci.9,addr=0x0 \
        -device pcie-root-port,port=0x14,chassis=10,id=pci.10,bus=pcie.0,addr=0x6.0x2 \
                -device vfio-pci,host=0000:0e:00.0,id=hostdev1,bus=pci.10,addr=0x0 \
        -device pcie-root-port,port=0x11,chassis=13,id=pci.13,bus=pcie.0,addr=0x6.0x3 \
                -device virtio-scsi-pci,iothread=iothread1,id=scsi0,num_queues=8,bus=pci.13,addr=0x0 \
        -m 8192 \
        -smp 4,sockets=1,dies=1,cores=4,threads=1 \
        -object iothread,id=iothread1 \
        -object memory-backend-file,id=shmmem-shmem0,mem-path=/dev/shm/looking-glass-testmachine,size=33554432,share=yes \
        -drive if=pflash,format=raw,readonly=on,file=/usr/share/ovmf/x64/OVMF_CODE.fd \
        -drive if=pflash,format=raw,readonly=on,file=/usr/share/ovmf/x64/OVMF_VARS.fd \
        -device virtio-scsi-pci,bus=pcie.0,id=scsi2,addr=0x8 \
                -device scsi-hd,drive=libvirt-1-format,bus=scsi2.0,id=scsi0-0-0-0,channel=0,scsi-id=0,lun=0,device_id=drive-scsi0-0-0-0,bootindex=2,write-cache=on \
                        -blockdev '{"driver":"file","filename":"/home/anton/windows_passthrough.qcow2","aio":"threads","node-name":"libvirt-1-storage","cache":{"direct":true,"no-flush":fals>
                        -blockdev '{"node-name":"libvirt-1-format","read-only":false,"discard":"unmap","cache":{"direct":true,"no-flush":false},"driver":"qcow2","file":"libvirt-1-storage",">
        -device pcie-root-port,multifunction=on,bus=pcie.0,id=port9-0,addr=0x9,chassis=0 \
                -device virtio-net-pci,mac=FE:00:00:00:00:00,id=network0,netdev=network0.0,status=on,bus=port9-0 \
                        -netdev tap,ifname=tapWin,id=network0.0,script=no,downscript=no

        # -device ich9-intel-hda \
        #       -device hda-micro,audiodev=hda \
        #               -audiodev pa,id=hda,server=unix:/run/user/$UID/pulse/native \

# -drive file=/home/anton/Downloads/Win10_20H2_v2_English_x64.iso,media=cdrom,if=none,format=raw,cache=none,id=cdrom0 \
# --cdrom /home/anton/Downloads/virtio-win-0.1.185.iso
