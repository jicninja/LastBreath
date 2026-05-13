using NUnit.Framework;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;
using LastBreath.Editor.Level;

namespace LastBreath.Levels.Tests
{
    public class {{SceneName}}InvariantsTests
    {
        private const string ScenePath = "src/Assets/Scenes/{{SceneName}}.unity";

        [Test]
        public void Validate_{{SceneName}}_PassesInvariants()
        {
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            var report = LevelSpec.ValidateScene(scene);
            Assert.IsTrue(report.IsOk, "{{SceneName}} failed invariants:\n" + report.ToString());
        }

        [Test]
        public void Roundtrip_{{SceneName}}_IsIdempotent()
        {
            var report = LevelSpec.RoundtripCheck(ScenePath);
            Assert.IsTrue(report.IsOk, "{{SceneName}} failed idempotency:\n" + report.ToString());
        }
    }
}
