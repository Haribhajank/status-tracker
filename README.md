# Status Tracker Project

## Overview
This application is an event driven status tracker (using WebSockets). It monitors various provider feeds (designed to, but currently only OpenAI) and pushes real time updates to the server. It is built to be scalable by reading provider configurations from a dynamic json file. This means we can add new providers without needing to rebuild or restart the system.

I have created a docker based (containerized it) solution.

## Building the Image
Open command line interface and navigate to project directory. 
Type in terminal 
```(docker build -t status-tracker .)```

## Running the Container
Start the container 
```(docker run -p 8000:8000 -v "%cd%":/app status-tracker)```

## Testing the Application
We can see the events happening in the console , also as for testing purposes only , i have also included a mock event trigger for a dummy status update , so that event driven functionality can be checked (uncomment it and hit the `/test-event` route).


## Adding New Providers
Open providers.dot json file and add a new entry with the provider name and their rss feed address.
