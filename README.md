# special succotash

## HOW TO RUN

### Prerequisites
- Docker
- Docker-compose

### Setup Instructions
1. Clone the repository.
2. Unzip the data.zip file in the same directory as data.zip.
3. Change the environment flag in `docker-compose.yml` file for `IMPORT_CSV_TO_MONGODB` to true.
4. Open the terminal and run `docker-compose up --build` command to build the Docker containers.
5. Wait for around 3 minutes for all the CSV data to be imported into the MongoDB database.

Once the above steps are completed, the development environment for the project is set up and ready to run.

### Running the project
To run the project, execute the following command:
```shell
docker-compose up -build
```
or run 
```shell
./run.sh # running docker-compose
./stop.sh # stopping  docker-compose
./database.sh # only run redis and Mongodb 
```

To run the shell script, you may need to give it executable permission. This can be done using the `chmod` command

```shell
chmod u+x run.sh
```