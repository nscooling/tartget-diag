// -----------------------------------------------------------------------------
// GPIO.h
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

#pragma once
#ifndef GPIO_H_
#define GPIO_H_

#include "Memory_map.h"
#include "Peripherals.h"
#include <cstdint>

// -----------------------------------------------------------------------------
// GPIO configuration
//
struct GPIO_register
{
  uint32_t mode;
  uint32_t type;
  uint32_t speed;
  uint32_t pull_up_down;
  uint32_t input;
  uint32_t output;
  uint32_t bit_set_reset;
  uint32_t lock;
  uint32_t alt_fn_low;
  uint32_t alt_fn_high;
};

// -----------------------------------------------------------------------------
// Register setup

constexpr uint32_t GPIO_base_address(STM32F407::AHB1_Device port)
{
  return static_cast<std::uint32_t>(
    (STM32F407::AHB1_base + (static_cast<unsigned>(port) * 0x400)));
}

uint32_t GPIO_set_bit_as_output(volatile GPIO_register* const port,
                                unsigned                      pin);

uint32_t GPIO_set_bit_as_input(volatile GPIO_register* const port,
                               unsigned                      pin);
uint32_t GPIO_set_bit(volatile GPIO_register* const port, unsigned pin);
uint32_t GPIO_clear_bit(volatile GPIO_register* const port, unsigned pin);
uint32_t GPIO_toggle_bit(volatile GPIO_register* const port, unsigned pin);

uint32_t GPIO_set_bits_as_output(volatile GPIO_register* const port,
                                 unsigned                      mask);

uint32_t GPIO_set_bits_as_input(volatile GPIO_register* const port,
                                unsigned                      mask);
uint32_t GPIO_set_bits(volatile GPIO_register* const port, uint16_t mask);
uint32_t GPIO_clear_bits(volatile GPIO_register* const port, uint16_t mask);
uint32_t GPIO_toggle_bits(volatile GPIO_register* const port, uint16_t mask);

#endif
