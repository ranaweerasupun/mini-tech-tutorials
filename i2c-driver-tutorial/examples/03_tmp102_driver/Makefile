obj-m += tmp102.o

KDIR := /lib/modules/$(shell uname -r)/build
PWD  := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

dtbo:
	dtc -@ -I dts -O dtb -o tmp102-overlay.dtbo tmp102-overlay.dts

install-overlay: dtbo
	sudo cp tmp102-overlay.dtbo /boot/overlays/
	@echo "Overlay installed. Add 'dtoverlay=tmp102-overlay' to /boot/firmware/config.txt"
	@echo "Then reboot for the overlay to take effect."

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f tmp102-overlay.dtbo
