// -----------------------------------------------------------------------------
// usart
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

#include <cstdint>
#include "USART_utils.h"

// Status register
typedef struct
{
  uint32_t          : 5;
  uint32_t RXNE     : 1;
  uint32_t          : 1;
  uint32_t TXE      : 1;
} UsartStatus;

// Data register
typedef union
{
  uint32_t tx;
  uint32_t rx;
} UsartData;

#define USART3_BASE 0x40004800u

static volatile UsartStatus *const sr = (UsartStatus*)(USART3_BASE);
static volatile UsartData *const dr = (UsartData*)(USART3_BASE + 0x04u);

void usart_init()
{
    STM32F407::USART_config::usart_configure();
}	

void usart_send(char c)
{
    while (sr->TXE == 0)
    { /* pass */}
    dr->tx = c;
}	

void usart_send_str (const char* str)
{
    while (*str) {
        usart_send(*str);
        str++;
    }
}	


bool usart_try_get(char *const holder)
{
    if (sr->RXNE == 0) {
        return false;
    }
    *holder = (char)dr->rx;
    return true;
}	

char usart_get()
{
    char ch;
    while (!usart_try_get(&ch)) {
        // pass
    }
    return ch;
}	

int main_usart(void)
{
    usart_init();
    
    usart_send_str("Enter characters (# to stop)? ");
    char ch;
    do {
        ch = usart_get();
        usart_send(ch);
    } while (ch != '#');
	return 0;
}
