# Practical Seminar Project
Welcome to the project repository for the practical seminar at the University of Regensburg. This repository contains the main components developed and evaluated during the seminar.

## General Project Structure

This project is divided into three main components, each housed in its own directory:

-   **`Plugin/`**: Contains a Camunda Modeler plugin that provides a user interface for ethical analysis of BPMN models. It allows users to select a process model, send it to the `EthicalAPI` for analysis, and visualize the results as a heatmap overlaid on the model.

-   **`EthicalAPI/`**: A Flask-based API that serves as the backend for the plugin. It receives process model data, orchestrates the ethical analysis by calling a Large Language Model (LLM), and returns the structured results.

-   **`Training-Pipeline/`**: Includes all the scripts and data necessary for the automated training, analysis, and evaluation of the ethical analysis pipeline. This is where the core logic for applying prompting techniques and using an LLM-as-judge resides. For more details, see the `README.md` inside this directory.

## Repository Structure

- **Plugin/**:
  This folder includes the main plugin developed as part of the project.

- **EthicalAPI/**:
  This folder contains the additional Ethical API Service.

- **Training-Pipeline/**:
  This folder contains the training pipeline as well as the data used for model training and evaluation.

## Getting Started

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Till1337/practical-seminar-ethics-bpmn-llm-extraction
    cd practical-seminar-ethics-bpmn-llm-extraction
    ```
2.  **Explore the Subfolders README.md files**