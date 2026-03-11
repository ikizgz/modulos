#!/usr/bin/env python3 
# -*- coding: utf-8 -*- 
"""
	modulo_factorial.py
	@param: número entero
	@return: factorial del número

	Copyright 2023 Ignacio Izaguerri

    __license__ = GPLv3
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

def factorial(n):
    c = n
    f = 1
    print(f'{c}! = ', end='')
    while(c > 0):
        if c>1:
            print(f'{c} x ', end='')
        else:
            print(f'{c} = ', end='')
        f *= c
        c -= 1
    return f

def main():
    print(__name__)
    print('Módulo para calcular el factorial de un número. Por ejemplo el de 7 es:')
    print(factorial(7))
    
if __name__ == '__main__':
    main()