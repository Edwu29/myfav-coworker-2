# Infrastructure and Deployment

## Infrastructure as Code
* **Tool**: AWS SAM CLI `1.100+`.
* **Location**: The infrastructure will be defined in the `template.yaml` file at the project's root directory.
* **Approach**: A single SAM template will define all AWS resources.

## Deployment Strategy
* **Strategy**: Continuous Deployment. Every merge to the `main` branch will automatically trigger a deployment to production.
* **CI/CD Platform**: **GitHub Actions**.
* **Pipeline Configuration**: The deployment workflow will be defined in a file located at `.github/workflows/deploy.yml`.

## Environments
* **Development**: The developer's local machine, using the `sam local` command suite for testing.
* **Production**: The live environment hosted on AWS.

## Environment Promotion Flow
Code is developed on a feature branch. Upon merging the PR to `main`, the GitHub Actions pipeline automatically builds, packages, and deploys the application to the `prod` environment.

## Rollback Strategy
* **Primary Method**: Re-deploying the previous stable version via AWS CloudFormation.

---