"""CTFd API client for interacting with CTFd platforms."""

import os
from typing import List, Optional, Dict, Any, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rich.console import Console

from .models import Challenge, User, Team, ScoreboardEntry, CTFInfo, Submission


class CTFdAPIError(Exception):
    """Custom exception for CTFd API errors."""
    pass


class CTFdClient:
    """CTFd API client."""

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        """Initialize CTFd client.

        Args:
            base_url: CTFd instance base URL
            token: API access token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1"
        self.token = token
        self.timeout = timeout
        self.console = Console()

        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set headers
        self.session.headers.update({
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/json',
            'User-Agent': 'CTFd-CLI/1.0.0'
        })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request with error handling.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response data

        Raises:
            CTFdAPIError: If API request fails
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        try:
            response = self.session.request(
                method, url, timeout=self.timeout, **kwargs
            )
            response.raise_for_status()

            if response.content:
                data = response.json()
                if not data.get('success', True):
                    raise CTFdAPIError(f"API Error: {data.get('message', 'Unknown error')}")
                return data.get('data', data)
            return {}

        except requests.exceptions.RequestException as e:
            raise CTFdAPIError(f"Request failed: {str(e)}")
        except ValueError as e:
            raise CTFdAPIError(f"Invalid JSON response: {str(e)}")

    def test_connection(self) -> bool:
        """Test API connection and token validity.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._make_request('GET', '/challenges')
            return True
        except CTFdAPIError:
            return False

    def get_ctf_info(self) -> CTFInfo:
        """Get comprehensive CTF information.

        Returns:
            CTF information with all available details
        """
        # Initialize default values
        ctf_info = {
            'name': "CTF",
            'description': None,
            'start': None,
            'end': None,
            'freeze': None,
            'mode': "users",
            'registration': True,
            'theme': None,
            'theme_header': None,
            'user_mode': None,
            'team_mode': None,
            'max_team_size': None,
            'verification_required': False,
            'workshop_mode': False,
            'paused': False,
            'rules': None,
            'contact_info': None
        }

        # Method 1: Try configs endpoint (most comprehensive)
        try:
            data = self._make_request('GET', '/configs')
            ctf_info.update({
                'name': data.get('ctf_name', ctf_info['name']),
                'description': data.get('ctf_description'),
                'theme': data.get('ctf_theme'),
                'theme_header': data.get('theme_header'),
                'user_mode': data.get('user_mode'),
                'team_mode': data.get('team_mode'),
                'registration': data.get('registration_visibility') != 'private',
                'verification_required': data.get('verify_emails', False),
                'workshop_mode': data.get('workshop_mode', False),
                'paused': data.get('paused', False),
                'max_team_size': data.get('team_size'),
            })

            # Parse datetime fields if available
            if data.get('start'):
                try:
                    from datetime import datetime
                    ctf_info['start'] = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
                except:
                    pass
            if data.get('end'):
                try:
                    from datetime import datetime
                    ctf_info['end'] = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
                except:
                    pass
            if data.get('freeze'):
                try:
                    from datetime import datetime
                    ctf_info['freeze'] = datetime.fromisoformat(data['freeze'].replace('Z', '+00:00'))
                except:
                    pass

        except CTFdAPIError:
            pass

        # Method 2: Try to get additional info from other endpoints
        try:
            # Check if teams mode is active
            teams_data = self._make_request('GET', '/teams/me')
            if teams_data:
                ctf_info['mode'] = "teams"
        except CTFdAPIError:
            pass

        # Method 3: Try to get rules/pages information
        try:
            pages_data = self._make_request('GET', '/pages')
            if isinstance(pages_data, list):
                for page in pages_data:
                    if page.get('route', '').lower() in ['rules', 'rule']:
                        ctf_info['rules'] = page.get('content')
                        break
        except CTFdAPIError:
            pass

        # Method 4: URL fallback for name
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(self.base_url)
            hostname = parsed_url.hostname
            if hostname and hostname != 'demo.ctfd.io' and ctf_info['name'] == "CTF":
                ctf_info['name'] = hostname.replace('.', ' ').title()
            elif hostname == 'demo.ctfd.io':
                ctf_info['name'] = "CTFd Demo"
        except:
            pass

        return CTFInfo(**ctf_info)

    def get_challenges(self) -> List[Challenge]:
        """Get all visible challenges.

        Returns:
            List of challenges
        """
        data = self._make_request('GET', '/challenges')
        challenges = []

        for challenge_data in data:
            # Get detailed challenge info
            detailed = self._make_request('GET', f"/challenges/{challenge_data['id']}")

            # Check if solved_by_me is available in the base data or detailed data
            solved_by_me = challenge_data.get('solved_by_me', detailed.get('solved_by_me', False))

            # Get current attempt count
            attempts = self.get_challenge_attempts(detailed['id'])

            challenge = Challenge(
                id=detailed['id'],
                name=detailed['name'],
                description=detailed['description'],
                category=detailed['category'],
                value=detailed['value'],
                tags=detailed.get('tags', []),
                state=detailed.get('state', 'visible'),
                max_attempts=detailed.get('max_attempts'),
                type=detailed.get('type', 'standard'),
                solves=detailed.get('solves', 0),
                files=detailed.get('files', []),
                hints=detailed.get('hints', []),
                solved_by_me=solved_by_me,
                attempts=attempts,
                connection_info=detailed.get('connection_info')
            )
            challenges.append(challenge)

        return challenges

    def get_challenge_attempts(self, challenge_id: int) -> int:
        """Get current attempt count for a challenge.

        Args:
            challenge_id: Challenge ID

        Returns:
            Number of attempts made for this challenge
        """
        try:
            # Try to get attempts from the challenge attempts endpoint
            data = self._make_request('GET', f'/challenges/{challenge_id}/attempts')
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict) and 'attempts' in data:
                return len(data['attempts'])
            return 0
        except CTFdAPIError:
            # If attempts endpoint is not available, try submissions
            try:
                # Get submissions for this challenge
                submissions_data = self._make_request('GET', '/submissions/me')
                if isinstance(submissions_data, list):
                    challenge_submissions = [s for s in submissions_data if s.get('challenge_id') == challenge_id]
                    return len(challenge_submissions)
                return 0
            except CTFdAPIError:
                # If both fail, return 0
                return 0

    def get_challenge_files(self, challenge_id: int) -> List[str]:
        """Get challenge file URLs.

        Args:
            challenge_id: Challenge ID

        Returns:
            List of file URLs
        """
        data = self._make_request('GET', f'/challenges/{challenge_id}')
        file_urls = []
        for file in data.get('files', []):
            # Handle both absolute URLs and relative file paths
            if file.startswith('http'):
                # Already a complete URL
                file_urls.append(file)
            elif file.startswith('/files/'):
                # Path already starts with /files/, just prepend base URL
                file_urls.append(f"{self.base_url}{file}")
            else:
                # Relative path without /files/ prefix
                file_path = file.lstrip('/')  # Remove leading slash if present
                file_urls.append(f"{self.base_url}/files/{file_path}")
        return file_urls

    def download_file(self, url: str, local_path: str) -> bool:
        """Download a file from CTFd.

        Args:
            url: File URL
            local_path: Local file path to save

        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()

            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True
        except Exception as e:
            self.console.print(f"[red]Failed to download {url}: {e}[/red]")
            return False

    def submit_flag(self, challenge_id: int, flag: str) -> Tuple[bool, str]:
        """Submit a flag for a challenge.

        Args:
            challenge_id: Challenge ID
            flag: Flag to submit

        Returns:
            Tuple of (success, message)
        """
        # Based on CTFd API documentation and user example, try different endpoints
        submission_attempts = [
            # Primary CTFd format - /challenges/attempt (without challenge ID in path)
            {
                'endpoint': '/challenges/attempt',
                'payload': {'challenge_id': challenge_id, 'submission': flag}
            },
            # Legacy format - /challenges/{id}/attempts
            {
                'endpoint': f'/challenges/{challenge_id}/attempts',
                'payload': {'submission': flag}
            },
            # Alternative submissions endpoint
            {
                'endpoint': '/submissions',
                'payload': {'challenge_id': challenge_id, 'submission': flag}
            },
            # Legacy format with 'flag' key
            {
                'endpoint': '/submissions',
                'payload': {'challenge': challenge_id, 'flag': flag}
            }
        ]

        last_error = None

        for attempt in submission_attempts:
            try:
                # Debug: print the endpoint and payload being tried
                self.console.print(f"[blue]Trying endpoint: {attempt['endpoint']} with payload: {attempt['payload']}[/blue]", style="dim")

                data = self._make_request(
                    'POST',
                    attempt['endpoint'],
                    json=attempt['payload']
                )

                # Handle different response formats
                if isinstance(data, dict):
                    status = data.get('status')
                    message = data.get('message', 'Unknown response')

                    # Some CTFd instances use 'success' instead of 'status'
                    if status is None and 'success' in data:
                        status = 'correct' if data['success'] else 'incorrect'

                    # Check for correct submission
                    is_correct = (
                        status == 'correct' or
                        status == 'success' or
                        data.get('success') is True or
                        (message.lower().startswith('correct') and not message.lower().startswith('incorrect'))
                    )

                    return is_correct, message
                else:
                    # Unexpected response format
                    return False, f"Unexpected response format: {data}"

            except CTFdAPIError as e:
                error_msg = str(e)
                last_error = error_msg
                self.console.print(f"[red]Endpoint {attempt['endpoint']} failed: {error_msg}[/red]", style="dim")

                # If we get a specific error that's not a 404, it might be the right endpoint
                if '404' not in error_msg and '403' not in error_msg:
                    return False, error_msg
                continue

        # If all endpoints failed, return the last error
        if last_error and '403' in last_error:
            return False, "Flag submission not allowed - this CTFd instance may not support API submissions or requires different permissions"
        else:
            return False, f"Could not find working submission endpoint. Last error: {last_error}"

    def get_scoreboard(self, count: int = 50) -> List[ScoreboardEntry]:
        """Get scoreboard.

        Args:
            count: Number of entries to retrieve

        Returns:
            List of scoreboard entries
        """
        data = self._make_request('GET', f'/scoreboard?count={count}')

        entries = []
        for i, entry in enumerate(data, 1):
            entries.append(ScoreboardEntry(
                pos=i,
                account_id=entry['account_id'],
                account_name=entry['name'],
                score=entry['score'],
                account_type=entry.get('type', 'user')
            ))

        return entries

    def get_user_solves(self, user_id: Optional[int] = None) -> List[int]:
        """Get solved challenges for a user.

        Args:
            user_id: User ID (None for current user)

        Returns:
            List of solved challenge IDs
        """
        # Try multiple endpoints that might contain solve information
        endpoints_to_try = [
            '/me/solves',
            '/me',
            '/submissions/me',
            '/teams/me/solves' if user_id is None else f'/users/{user_id}/solves'
        ]

        for endpoint in endpoints_to_try:
            try:
                data = self._make_request('GET', endpoint)

                # Different response formats for different endpoints
                if endpoint == '/me/solves' or 'solves' in endpoint:
                    if isinstance(data, list):
                        return [solve['challenge_id'] for solve in data if 'challenge_id' in solve]
                elif endpoint == '/me':
                    # Check if user data includes solves
                    if isinstance(data, dict) and 'solves' in data:
                        return [solve['challenge_id'] for solve in data['solves']]
                elif 'submissions' in endpoint:
                    # Check submissions for correct ones
                    if isinstance(data, list):
                        return [sub['challenge_id'] for sub in data if sub.get('type') == 'correct']

            except CTFdAPIError:
                continue

        # If all endpoints fail, use the challenges endpoint to check solve status
        # This is the most reliable method as it includes solved_by_me field
        try:
            challenges_data = self._make_request('GET', '/challenges')
            solved_ids = []
            for challenge_data in challenges_data:
                if challenge_data.get('solved_by_me', False):
                    solved_ids.append(challenge_data['id'])
            return solved_ids
        except:
            return []

    def get_me(self) -> Optional[User]:
        """Get current user information.

        Returns:
            Current user information or None if not available
        """
        try:
            data = self._make_request('GET', '/me')
            return User(
                id=data['id'],
                name=data['name'],
                email=data.get('email'),
                score=data.get('score', 0),
                place=data.get('place', 0),
                website=data.get('website'),
                affiliation=data.get('affiliation'),
                country=data.get('country')
            )
        except CTFdAPIError:
            return None

    def get_team_member_solves(self, user_id: int) -> List[int]:
        """Get solved challenges for a specific team member.

        Args:
            user_id: User ID

        Returns:
            List of solved challenge IDs
        """
        try:
            data = self._make_request('GET', f'/users/{user_id}/solves')
            return [solve['challenge_id'] for solve in data]
        except CTFdAPIError:
            return []

    def get_challenge_solvers(self) -> dict:
        """Get mapping of challenge ID to list of team members who solved it.

        Returns:
            Dictionary mapping challenge_id -> [list of user_ids who solved it]
        """
        try:
            # Get team info
            team_data = self._make_request('GET', '/teams/me')
            members = team_data.get('members', [])

            challenge_solvers = {}

            # For each team member, get their solves
            for member_id in members:
                try:
                    member_solves = self.get_team_member_solves(member_id)
                    for challenge_id in member_solves:
                        if challenge_id not in challenge_solvers:
                            challenge_solvers[challenge_id] = []
                        challenge_solvers[challenge_id].append(member_id)
                except CTFdAPIError:
                    continue

            return challenge_solvers

        except CTFdAPIError:
            return {}

    def get_team_info(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific team.

        Args:
            team_id: Team ID

        Returns:
            Team information dictionary or None if not found
        """
        try:
            return self._make_request('GET', f'/teams/{team_id}')
        except CTFdAPIError:
            return None

    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific user.

        Args:
            user_id: User ID

        Returns:
            User information dictionary or None if not found
        """
        try:
            return self._make_request('GET', f'/users/{user_id}')
        except CTFdAPIError:
            return None

    def get_team_solves(self, team_id: int) -> List[Dict[str, Any]]:
        """Get solved challenges for a specific team.

        Args:
            team_id: Team ID

        Returns:
            List of team solves
        """
        try:
            return self._make_request('GET', f'/teams/{team_id}/solves')
        except CTFdAPIError:
            return []

    def get_user_solves(self, user_id: int) -> List[Dict[str, Any]]:
        """Get solved challenges for a specific user.

        Args:
            user_id: User ID

        Returns:
            List of user solves
        """
        try:
            return self._make_request('GET', f'/users/{user_id}/solves')
        except CTFdAPIError:
            return []

    def search_teams(self, name: str) -> List[Dict[str, Any]]:
        """Search for teams by name.

        Args:
            name: Team name to search for

        Returns:
            List of teams matching the search
        """
        try:
            # Try to get all teams and filter by name
            # Some CTFd instances don't support search, so we'll get all and filter
            teams_data = self._make_request('GET', '/teams')
            if isinstance(teams_data, list):
                return [team for team in teams_data if name.lower() in team.get('name', '').lower()]
            return []
        except CTFdAPIError:
            return []

    def search_users(self, name: str) -> List[Dict[str, Any]]:
        """Search for users by name.

        Args:
            name: User name to search for

        Returns:
            List of users matching the search
        """
        try:
            # Try to get all users and filter by name
            users_data = self._make_request('GET', '/users')
            if isinstance(users_data, list):
                return [user for user in users_data if name.lower() in user.get('name', '').lower()]
            return []
        except CTFdAPIError:
            return []