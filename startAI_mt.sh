#!/bin/bash
# edit for directory of AI code and model directories
cd /home/ai/ncs

# should be clean shutdown
/usr/bin/pkill -2 -f "AI_mt.py" > /dev/null 2>&1
sleep 5

# but, make sure it goes away before retrying in case its hung
/usr/bin/pkill -9 -f "AI_mt.py" > /dev/null 2>&1
sleep 1

./AI_mt.py >> ./`/bin/date +%F`_AI.log 2>&1 &

