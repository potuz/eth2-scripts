#!/bin/bash

root=$(echo $1 | base64 -d | od -An -t x1 | tr -d ' \n')
echo $root
