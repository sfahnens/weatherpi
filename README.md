# weatherpi

Simple logger/display for the raspberry pi and cheap temperature / humidity sensors.   
Docker image based on rtl_433, influxdb, grafana.

## On Build:

### One time setup for cross architecture building:
- download buildx
- put it to ~/.docker/cli-plugins
- enable docker experimental features

```
sudo apt-get install -y docker.io qemu-user-static binfmt-support
sudo docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

docker buildx create --name strawberry-builder
docker buildx use  strawberry-builder
docker buildx inspect --bootstrap
docker buildx build -t"buildx-test:latest" --builder strawberry-builder --platform linux/arm/v7 docker
```

### Build the image
Launch the builder (once per boot?!):
```
docker buildx inspect --bootstrap
```

Build the docker image:
```
docker buildx build -t "weatherpi:latest" \
--builder strawberry-builder \
--platform linux/arm/v7 \
--output type=tar,dest=- docker \
| gzip >  weatherpi.tar.gz
```

Copy the image and the naming rules to the server:
```
scp weatherpi.tar.gz weatherpi_naming_rules.txt root@strawberry:
```

## On Server:

Import the image under a specified name:
```
docker image import weatherpi.tar.gz weatherpi:latest
```

Run the container (make sure all mounts exist):
```
docker run -d --name weatherpi \
-p 3003:3003 -p 3004:8083 -p 8086:8086 \
-v /data/influxdb:/var/lib/influxdb \
-v /data/grafana:/var/lib/grafana \
-v /root/weatherpi_naming_rules.txt:/root/naming_rules.txt \
--device=/dev/bus/usb \
weatherpi:latest /run.sh
```

Launch bash inside the running container:
```
docker exec -it weatherpi /bin/bash
```

## On Client:

Browse to strawberry:3003

If the ports are not open tunnel grafana with:
```
ssh -N -L 3003:localhost:3003 pi@strawberry 
```

Or tunnel everything (grafana, management, influxdb):
```
ssh -N -L 3003:localhost:3003 -L 3004:localhost:3004 -L 3005:localhost:8086 pi@strawberry 
```

## Misc / Notes

https://github.com/philhawthorne/docker-influxdb-grafana
```
python3 weatherpi.py --rtl_433_bin /usr/local/bin/rtl_433 --verbose
python3 weatherpi.py --rtl_433_bin /usr/local/bin/rtl_433 --naming_rules /root/naming_rules.txt
```
