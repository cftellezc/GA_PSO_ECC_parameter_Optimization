# Comparative Analysis of Genetic Algorithm (GA) and Particle Swarm Optimization (PSO) in ECC Optimization

This repository contains the code and resources for a comprehensive analysis between two vital artificial intelligence algorithms, **GA** and **PSO**, focusing on the optimization of **Elliptic Curve Cryptography (ECC)** parameters. The research emphasizes implications for enhancing cybersecurity in third-party e-commerce integrations, especially in the pre-quantum era.

## Introduction

We explore and compare the **Genetic Algorithm (GA)** and **Particle Swarm Optimization (PSO)** to optimize ECC parameters, such as the elliptic curve coefficients, prime number, generator point, group order, and cofactor. The analysis is conducted in a simulated e-commerce environment, with a strong focus on traditional computing. For detailed insights into the study's methodology and findings, please refer to the corresponding paper.

## Main Findings

- **Robust Optimization Techniques**: Incorporation of Pollard's rho attack and Hasse's theorem for optimization precision.
- **Performance Comparison**: Insights into which bio-inspired algorithm yields better optimization results.
- **Simulated E-commerce Testing**: Contrast with well-known curves like secp256k1 in the transmission of order messages using ECDH and HMAC.
- **Implications and Recommendations**: Highlighting the effectiveness of GA and PSO in ECC optimization, with recommendations for immediate consideration.

## Implementation

The implementation is divided into two main groups: **ECC Params Optimization** and **e-commerce Simulation**. Each consists of applications and software modules built using **Python**.

### A. ECC Params Optimization Group
- **Genetic Algorithm**: Implemented in `GA.py`, employing the DEAP library.
- **Particle Swarm Optimization**: Implemented in `PSO.py`.
- **ECC Parameters Files**: Contains best parameters found by GA and PSO (`ga_ecc_params.txt` and `pso_ecc_params.txt`).
- **Utility Module**: `ai_ecc_utils.py` for assisting the creation of elliptic curves.

### B. E-commerce Simulation Group
- **Standard Curves File**: `well-known_curves_params.txt` for standard cryptography curves.
- **ECC Utility Module**: `ecc.py` for reading and structuring ECC parameters.
- **Orders Dataset**: Invoices converted into order data for practical simulation.
- **EntityA and EntityB**: Emulated e-commerce solution (`EntityA.py`) and simulated ERP server (`EntityB.py`) using Flask.
- **Pollard's Rho Attack**: `pollards_rho_attack.py` to attack communication between entities and evaluate ECC parameters.

## Recommendations

Given the striking efficacy of GA and PSO in ECC optimization, we recommend immediate consideration of these findings for enhancing cybersecurity in third-party e-commerce integrations, especially in the context of pre-quantum computing era.

## How to Run

Details on how to run the scripts and use the provided components can be found in the respective documentation within the repository.

## License

This project is licensed under the UNAL License - see the LICENSE.md file for details.

## Acknowledgments

We would like to thank all contributors and the community for supporting this research.
