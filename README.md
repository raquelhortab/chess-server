# project moved to another repository -> this is not updated!

# chess-server

## Build the docker container

```
$ docker build -t chess-server .
```

## Run the docker container

```
$ docker run -p 80:80 --name chess -it chess-server
```

And redirect the browser to `http://127.0.0.1`.

## python-chess

Check : [python-chess documentation](http://0.0.0.0:3000/chess/20?game=94ccc4&new_game=false) and [python-chess on github](https://github.com/niklasf/python-chess/)
