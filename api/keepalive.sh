if [ -f "DONTSTART" ]; then
  exit 0;
fi

count=`ps aux|grep api-uwsgi.sock | grep -v grep | wc -l`
response=`curl http://api.indextank.com/ 2> /dev/null`

if [ "$response" != "\"IndexTank API. Please refer to the documentation: http://indextank.com/documentation/api\"" ]; then
  date
  echo Restarting webapp. Process count is $count, response was:
  echo "$response"
  ./dokillapi.sh
  sleep 5s
  ./dostartapi.sh
fi

