/*
 * DEBUGGER code
 * 
 * On "publish", when buffer is free, debugger stores arbitrary variables 
 * content into, and mark this buffer as filled
 * 
 * 
 * Buffer content is read asynchronously, (from non real time part), 
 * and then buffer marked free again.
 *  
 * 
 * */
#include"plc_app.h"
#include "iec_types_all.h"
#include "POUS.h"
/*for memcpy*/
#include <string.h>
#include <stdio.h>

int RetainCmp(unsigned int offset, unsigned int count, void *p);
void RetainBufferClose();
#ifndef TARGET_ONLINE_DEBUG_DISABLE
#define BUFFER_SIZE %(buffer_size)d

/* Atomically accessed variable for buffer state */
#define BUFFER_FREE 0
#define BUFFER_BUSY 1
long buffer_state = BUFFER_FREE;

/* The buffer itself */
char debug_buffer[BUFFER_SIZE];

/* Buffer's cursor*/
char* buffer_cursor = debug_buffer;
#endif

unsigned int retain_offset = 0;
/***
 * Declare programs 
 **/
%(programs_declarations)s

/***
 * Declare global variables from resources and conf 
 **/
%(extern_variables_declarations)s

const dbgvardsc_t dbgvardsc[] = {
%(variable_decl_array)s
};
unsigned int sizeof_dbgvardsc=sizeof(dbgvardsc)/ sizeof(dbgvardsc_t);

