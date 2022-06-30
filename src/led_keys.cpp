// -----------------------------------------------------------------------------
// main.cpp
//
// DISCLAIMER:
// Feabhas is furnishing this item "as is". Feabhas does not provide any
// warranty of the item whatsoever, whether express, implied, or statutory,
// including, but not limited to, any warranty of merchantability or fitness
// for a particular purpose or any warranty that the contents of the item will
// be error-free.
// In no respect shall Feabhas incur any liability for any damages, including,
// but limited to, direct, indirect, special, or consequential damages arising
// out of, resulting from, or any way connected to the use of the item, whether
// or not based upon warranty, contract, tort, or otherwise; whether or not
// injury was sustained by persons or property or otherwise; and whether or not
// loss was sustained from, or arose out of, the results of, the item, or any
// services that may be provided by Feabhas.
// -----------------------------------------------------------------------------

#include <iostream>
#include <cstdio>
#include "Timer.h"

constexpr uint32_t GPIOD_BASE {0x40020C00u};

static volatile uint32_t *const AHB1_enable {reinterpret_cast<uint32_t*>(0x40023830u)};
static volatile uint32_t *const GPIOD_moder {reinterpret_cast<uint32_t*>(GPIOD_BASE)};
static volatile uint32_t *const GPIOD_outr {reinterpret_cast<uint32_t*>(GPIOD_BASE + 0x14u)};
static volatile const uint32_t *const GPIOD_idr {reinterpret_cast<uint32_t*>(GPIOD_BASE + 0x10u)};

inline bool test(volatile uint32_t *const port, uint32_t pattern) 
{
    return (*port & pattern) != 0;
}

inline void set(volatile uint32_t *const port, uint32_t pattern) 
{
    uint32_t value = *port;
    value |= pattern; 
    *port = value;
}

inline void clear(volatile uint32_t *const port, uint32_t pattern) 
{
    uint32_t value = *port;
    value &= ~pattern; 
    *port = value;
}

enum Inputs {door=0, PS1, PS2, PS3, cancel, accept, sensor};
enum Outputs {led_a=8, led_b, led_c, led_d, motor, direction, latch};

int main(void)
{
	sleep(3000);
    set(AHB1_enable, 0x1u << 3); 

    clear(GPIOD_moder, 0x3FFFu << led_a*2); 
	set(GPIOD_moder, 0x1555u << led_a*2); 

    unsigned int led = led_a;
	bool dir = false;
    for(;;)
    {
        puts("loop");
		if ((*GPIOD_idr & (0x1u << door)) != 0) {
			puts("door open");
			while ((*GPIOD_idr & (0x1u << door)) != 0) 
			{ }
			printf("** pskeys %d\n", static_cast<int>((*GPIOD_idr >> PS1) & 0b111u));
		}
        set(GPIOD_outr, 0x1u << led);
        sleep(1000);
		clear(GPIOD_outr, 0x1u << led);
		sleep(500);
        led = (led != led_d) ? led + 1 : led_a+0;
		uint32_t port = *GPIOD_idr;
		if ((port & (0x1u << accept)) != 0) {
			puts("** motor on");
		    set(GPIOD_outr, 0x1u << motor);
			set(GPIOD_outr, 0x1u << latch);
		}
		else if ((port & (0x1u << cancel)) != 0) {
			puts("** motor off");
		    clear(GPIOD_outr, 0x1u << motor);
			clear(GPIOD_outr, 0x1u << latch);
		}
		else if ((port & (0x1u << PS3)) != 0) {
			printf("** motor dir %d\n", dir);
			dir = !dir;
		    if (dir) {
				set(GPIOD_outr, 0x1u << direction);
			}
			else {
				clear(GPIOD_outr, 0x1u << direction);
			}
		}
    }
}
