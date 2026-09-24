import unittest
import asyncio
from unittest.mock import patch, MagicMock

from backend.orchestrator import orchestrate_task
from backend.tools.planner import plan_task_from_natural_language
from backend.tools.browser_control import (
    play_media,
    select_media_result,
    verify_playback_state,
    fetch_youtube_search_results,
)
from backend.task_manager import task_manager

class SearchVsPlayTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        task_manager.tasks.clear()
        task_manager.active_task_id = None
        task_manager._pause_requested = False
        task_manager._cancel_requested = False

    # 1. "Search YouTube for X" -> search only (does not play)
    def test_01_search_youtube_only(self):
        plan = plan_task_from_natural_language("Search YouTube for Arijit Singh")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["tool"], "browser.search")
        self.assertEqual(plan[0]["arguments"]["engine"], "youtube")
        self.assertEqual(plan[0]["arguments"]["query"], "Arijit Singh")
        # Ensure it is NOT play_media
        self.assertNotEqual(plan[0]["tool"], "browser.play_media")

    # 2. "Play X on YouTube" -> search + select + open + playback verification
    def test_02_play_media_on_youtube_intent(self):
        plan = plan_task_from_natural_language("Play Soong Yeshanagula Anirudh on YouTube")
        self.assertIsNotNone(plan)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["tool"], "browser.play_media")
        self.assertIn("Yeshanagula Anirudh", plan[0]["arguments"]["query"])
        self.assertEqual(plan[0]["arguments"]["platform"], "youtube")
        self.assertEqual(plan[0]["arguments"]["criteria"], "best_match")

    # 3. "Play the first result" / "Play the first Minecraft video" -> dynamic result selection
    def test_03_play_first_result_intent(self):
        plan1 = plan_task_from_natural_language("Play the first result")
        self.assertIsNotNone(plan1)
        self.assertEqual(plan1[0]["tool"], "browser.play_media")
        self.assertEqual(plan1[0]["arguments"]["criteria"], "first")

        plan2 = plan_task_from_natural_language("Play the first Minecraft video")
        self.assertIsNotNone(plan2)
        self.assertEqual(plan2[0]["tool"], "browser.play_media")
        self.assertEqual(plan2[0]["arguments"]["criteria"], "first")
        self.assertIn("Minecraft", plan2[0]["arguments"]["query"])

    # 4. Playback blocked by popup -> observe + handle popup + retry
    def test_04_playback_blocked_by_popup_adaptation(self):
        action_log = []
        turn_counter = [0]

        def mock_obs():
            turn_counter[0] += 1
            if turn_counter[0] == 1:
                # First observation: Cookie/Consent dialog blocking player
                return {
                    "active_window": {"title": "YouTube - Google Chrome"},
                    "ui_elements": [
                        {"name": "Before you continue to YouTube", "type": "Text"},
                        {"name": "Accept all", "type": "Button", "bounding_box": {"center_x": 500, "center_y": 600}},
                    ],
                    "visible_windows": [{"title": "YouTube - Google Chrome"}],
                }
            else:
                # Second observation: Popup dismissed, video actively playing
                return {
                    "active_window": {"title": "Yeshanagula - YouTube - Google Chrome"},
                    "ui_elements": [
                        {"name": "Pause (k)", "type": "Button"},
                    ],
                    "visible_windows": [{"title": "Yeshanagula - YouTube - Google Chrome"}],
                }

        def mock_act(action_name):
            action_log.append(action_name)

        ver_res = verify_playback_state(
            expected_title="Yeshanagula",
            timeout_seconds=4.0,
            adapt_if_needed=True,
            observation_fn=mock_obs,
            action_fn=mock_act,
        )

        self.assertTrue(ver_res["verified"])
        self.assertTrue(ver_res["playing"])
        self.assertIn("dismiss_popup", action_log)
        self.assertIn("Yeshanagula", ver_res["title"])

    # 5. Playback still loading -> observe/wait + verify
    def test_05_playback_loading_wait_and_verify(self):
        turn_counter = [0]

        def mock_obs():
            turn_counter[0] += 1
            if turn_counter[0] < 3:
                # Loading spinner / blank title
                return {
                    "active_window": {"title": "Loading..."},
                    "ui_elements": [],
                    "visible_windows": [],
                }
            else:
                # Loaded and actively playing
                return {
                    "active_window": {"title": "Arijit Singh - Kesariya - YouTube - Google Chrome"},
                    "ui_elements": [
                        {"name": "Pause (k)", "type": "Button"},
                    ],
                    "visible_windows": [{"title": "Arijit Singh - Kesariya - YouTube - Google Chrome"}],
                }

        ver_res = verify_playback_state(
            expected_title="Kesariya",
            timeout_seconds=5.0,
            adapt_if_needed=True,
            observation_fn=mock_obs,
        )

        self.assertTrue(ver_res["verified"])
        self.assertTrue(ver_res["playing"])
        self.assertIn("Kesariya", ver_res["title"])

    # 6. Playback fails -> report failure instead of false success
    def test_06_playback_fails_reports_failure(self):
        def mock_obs():
            # Never plays (black screen / error)
            return {
                "active_window": {"title": "Video unavailable - YouTube - Google Chrome"},
                "ui_elements": [{"name": "This video is unavailable", "type": "Text"}],
                "visible_windows": [],
            }

        ver_res = verify_playback_state(
            expected_title="Unavailable Video",
            timeout_seconds=1.0,
            adapt_if_needed=False,
            observation_fn=mock_obs,
        )

        self.assertFalse(ver_res["verified"])
        self.assertFalse(ver_res["playing"])
        self.assertIn("failed", ver_res["error"].lower())

    # 7. Autoplay restriction handling: paused -> triggers play toggle -> verified
    def test_07_autoplay_blocked_adaptation(self):
        turn_counter = [0]
        action_log = []

        def mock_obs():
            turn_counter[0] += 1
            if turn_counter[0] == 1:
                # Autoplay blocked, player is paused
                return {
                    "active_window": {"title": "Minecraft Ep 1 - YouTube - Google Chrome"},
                    "ui_elements": [{"name": "Play (k)", "type": "Button"}],
                    "visible_windows": [{"title": "Minecraft Ep 1 - YouTube - Google Chrome"}],
                }
            else:
                # Play toggle sent, now playing
                return {
                    "active_window": {"title": "Minecraft Ep 1 - YouTube - Google Chrome"},
                    "ui_elements": [{"name": "Pause (k)", "type": "Button"}],
                    "visible_windows": [{"title": "Minecraft Ep 1 - YouTube - Google Chrome"}],
                }

        def mock_act(action_name):
            action_log.append(action_name)

        ver_res = verify_playback_state(
            expected_title="Minecraft Ep 1",
            timeout_seconds=4.0,
            adapt_if_needed=True,
            observation_fn=mock_obs,
            action_fn=mock_act,
        )

        self.assertTrue(ver_res["verified"])
        self.assertTrue(ver_res["playing"])
        self.assertIn("toggle_play", action_log)

    # 8. Dynamic candidate selection chooses best match
    def test_08_dynamic_result_selection(self):
        candidates = [
            {"title": "Minecraft Official Trailer 2024", "url": "https://youtube.com/watch?v=11111111111"},
            {"title": "Yeshanagula Official Song | Anirudh Ravichander", "url": "https://youtube.com/watch?v=22222222222"},
            {"title": "Python Tutorial for Beginners", "url": "https://youtube.com/watch?v=33333333333"},
        ]

        with patch("backend.tools.browser_control.open_url", return_value={"success": True, "browser": "Chrome"}):
            # Should select the Anirudh song based on query overlap
            res = select_media_result(
                query="Soong Yeshanagula Anirudh",
                platform="youtube",
                criteria="best_match",
                candidates=candidates,
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["url"], "https://youtube.com/watch?v=22222222222")
            self.assertIn("Yeshanagula", res["title"])

            # Should select first candidate when criteria is 'first'
            res_first = select_media_result(
                query="Whatever",
                platform="youtube",
                criteria="first",
                candidates=candidates,
            )
            self.assertTrue(res_first["success"])
            self.assertEqual(res_first["url"], "https://youtube.com/watch?v=11111111111")
            self.assertIn("Minecraft", res_first["title"])

    # 9. Orchestrator enforces completion requirements: never reports false success if play verification fails
    async def test_09_orchestrator_play_enforces_verification(self):
        from backend.tools.registry import tool_registry
        play_tool = tool_registry.get("browser.play_media")
        orig_fn = play_tool.execute_fn
        try:
            # Case A: Playback succeeds
            play_tool.execute_fn = MagicMock(return_value={
                "success": True,
                "action": "play_media",
                "platform": "youtube",
                "title": "Yeshanagula Song",
                "url": "https://www.youtube.com/watch?v=zG6ZaJN0VQ8",
                "verified": True,
                "message": "Now playing 'Yeshanagula Song' on YouTube.",
            })
            res_success = await orchestrate_task(user_input="Play Soong Yeshanagula Anirudh on YouTube")
            self.assertEqual(res_success["status"], "SUCCESS")
            self.assertIn("playing", res_success["response"].lower())
            self.assertIn("yeshanagula", res_success["response"].lower())

            # Case B: Playback fails verification -> MUST report ERROR, never false success
            play_tool.execute_fn = MagicMock(return_value={
                "success": False,
                "action": "play_media",
                "platform": "youtube",
                "verified": False,
                "error": "Playback verification failed: Media player did not start within timeout.",
                "message": "Failed to verify playback.",
            })
            res_fail = await orchestrate_task(user_input="Play Soong Yeshanagula Anirudh on YouTube")
            self.assertEqual(res_fail["status"], "ERROR")
            self.assertNotIn("now playing", res_fail["response"].lower())
            self.assertIn("verification failed", res_fail["response"].lower())
        finally:
            play_tool.execute_fn = orig_fn

    # 10. "Find a Minecraft video" vs "Play the first Minecraft video"
    def test_10_find_vs_play_intent_differentiation(self):
        search_plan = plan_task_from_natural_language("Find a Minecraft video")
        self.assertEqual(search_plan[0]["tool"], "browser.search")

        play_plan = plan_task_from_natural_language("Play the first Minecraft video")
        self.assertEqual(play_plan[0]["tool"], "browser.play_media")
        self.assertEqual(play_plan[0]["arguments"]["criteria"], "first")

if __name__ == "__main__":
    unittest.main()

