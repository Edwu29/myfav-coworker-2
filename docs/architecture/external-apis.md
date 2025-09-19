# External APIs

## GitHub API
* **Purpose**: To handle user authentication via OAuth2 and to fetch repository and pull request data on behalf of the authenticated user.
* **Documentation**: `https://docs.github.com/en/rest`
* **Base URL**: `https://api.github.com`
* **Authentication**: OAuth2. We will use the user's access token obtained via the server-side flow. This will require the `repo` scope to access private repository data.
* **Rate Limits**: The standard authenticated rate limit is 5,000 requests per hour, which is more than sufficient for the MVP.
* **Key Endpoints Used**:
    * `POST /login/oauth/access_token`: To exchange the temporary code for an access token.
    * `GET /user`: To fetch the authenticated user's profile information.
    * `GET /repos/{owner}/{repo}/pulls/{pull_number}`: To fetch the details for a specific pull request.
* **Integration Notes**: All interactions with this API will be encapsulated within the **GitHub Service** component to ensure a clean separation of concerns.

---