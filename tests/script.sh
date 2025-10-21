#!/bin/bash

URL="http://192.168.0.94:5050/fetch-emails"

while true
do
  echo "----- $(date) -----"
  curl -s "$URL"
  echo -e "\n"
  sleep 15
done
