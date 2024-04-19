#!/bin/bash
# Define the number of projects
NUM_PROJECTS=1000

echo "Generating $NUM_PROJECTS project plans..."
python3 generate_deliverable.py $NUM_PROJECTS

echo "Generation complete."
