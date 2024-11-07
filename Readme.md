docker build -t searchgpt .

docker run -p 80:80 --env-file .env searchgpt 