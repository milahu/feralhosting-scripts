#/bin/sh

pid=$(pidof -s rqbit)

while true; do
  # ps -p $pid -o %cpu,%mem,cmd
  # https://stackoverflow.com/a/52751050
  # top -b -n 2 -d 0.2 -p $pid | tail -1 | awk '{print $9}'
  # top -b -n 2 -d 0.2 -p $pid | tail -1 | awk '{print $9}'
  # pidstat -h -r -u -v -p $pid
  pidstat -h -r -u -v -p $(pidof -s rqbit) 1 1
  sleep 1
done
