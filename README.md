# WE-DJ

## Project info

**Frontend is available on another repository**: https://github.com/Max-Changg/WE-DJ/tree/main

**Developer URL**: https://lovable.dev/projects/7cf7966f-71a7-4e7a-8d64-e9736a1f9cd7

## What is WE-DJ?

WE-DJ is an AI DJ that recommends songs to transition to and generates the transitions between songs. arms both beginner and expert DJs with a powerful set of tools to improve their musical capabilities. For those just getting started, this mixing assistance can eliminate the typically jarring transitions associated with inexperience. The music suggestions, tailored to beat, genre, and key, help maintain an unmatched level of energy to the setlist.

## How does it work?

The pipeline is as follows:
 - User inputs a song
 - WE-DJ finds the top 10 most similar, transition-worthy songs using our custom recommendation system
 - WE-DJ then uses generative AI to generate a transition between the current song and another
 - Finally, WE-DJ repeats these steps with the next song, making a seamless transitionable playlist!

## What technologies did we use for this project?

This project is built with:

- Python
- TypeScript
- React
- Vite
- shadcn-ui
- Tailwind CSS
