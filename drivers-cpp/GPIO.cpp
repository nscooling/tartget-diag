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

#include "GPIO.h"

uint32_t GPIO_set_bit_as_output(volatile GPIO_register* const port,
                                unsigned                      pin)
{
  auto moder = port->mode;
  moder &= ~(0b11u << (static_cast<unsigned>(pin) * 2));
  moder |= (0b01u << (static_cast<unsigned>(pin) * 2));
  port->mode = moder;
  return moder;
}

uint32_t GPIO_set_bit_as_input(volatile GPIO_register* const port, unsigned pin)
{
  auto moder = port->mode;
  moder &= ~(0b11u << (static_cast<unsigned>(pin) * 2));
  port->mode = moder;
  return moder;
}

uint32_t GPIO_set_bits_as_output(volatile GPIO_register* const port,
                                 unsigned                      mask)
{
  auto moder = port->mode;
  for (unsigned pin = 0; pin < 32; ++pin) {
    if ((mask & (0x1u << pin)) != 0) {
      moder &= ~(0b11u << (static_cast<unsigned>(pin) * 2));
      moder |= (0b01u << (static_cast<unsigned>(pin) * 2));
    }
  }
  port->mode = moder;
  return moder;
}

uint32_t GPIO_set_bits_as_input(volatile GPIO_register* const port,
                                unsigned                      mask)
{
  auto moder = port->mode;
  for (unsigned pin = 0; pin < 32; ++pin) {
    if ((mask & (0x1u << pin)) != 0) {
      moder &= ~(0b11u << (static_cast<unsigned>(pin) * 2));
    }
  }
  port->mode = moder;
  return moder;
}

uint32_t GPIO_set_bit(volatile GPIO_register* const port, unsigned pin)
{
  auto odr = port->output;
  odr |= (0x1u << static_cast<unsigned>(pin));
  port->output = odr;
  return port->input;
}
uint32_t GPIO_set_bits(volatile GPIO_register* const port, uint16_t mask)
{
  auto odr = port->output;
  odr |= mask;
  port->output = odr;
  return port->input;
}
uint32_t GPIO_clear_bit(volatile GPIO_register* const port, unsigned pin)
{
  auto odr = port->output;
  odr &= ~(0x1u << static_cast<unsigned>(pin));
  port->output = odr;
  return port->input;
}
uint32_t GPIO_clear_bits(volatile GPIO_register* const port, uint16_t mask)
{
  uint32_t odr = port->output;
  odr &= ~static_cast<uint32_t>(mask);
  port->output = odr;
  return port->input;
}

uint32_t GPIO_toggle_bit(volatile GPIO_register* const port, unsigned pin)
{
  auto odr = port->output;
  odr ^= (0x1u << static_cast<unsigned>(pin));
  port->output = odr;
  return port->input;
}

uint32_t GPIO_toggle_bits(volatile GPIO_register* const port, uint16_t mask)
{
  auto odr = port->output;
  odr ^= mask;
  port->output = odr;
  return port->input;
}

