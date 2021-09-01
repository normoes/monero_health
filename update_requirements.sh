#!/bin/bash

set -Eeo pipefail

current_date=$(LC_ALL=en_US.utf8 date --utc)

echo -e "\e[32mCompile python dependencies.\e[39m"
pip-compile --rebuild --upgrade --output-file requirements.txt requirements.in
sed -i "1i# Compile date: $current_date" requirements.txt

echo -e "\e[32mDone. Check requirements.txt.\e[39m"
