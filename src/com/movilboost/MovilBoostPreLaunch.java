package com.movilboost;

import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.loader.api.entrypoint.PreLaunchEntrypoint;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Aplica los ajustes basicos de FPS una sola vez, sin pisar el resto de tu options.txt. */
public class MovilBoostPreLaunch implements PreLaunchEntrypoint {
    private static final String[][] OPTS = {
            {"renderDistance", "8"},
            {"simulationDistance", "5"},
            {"graphicsMode", "0"},
            {"particles", "2"},
            {"maxFps", "120"},
            {"enableVsync", "false"},
            {"entityShadows", "false"},
            {"biomeBlendRadius", "1"},
            {"mipmapLevels", "2"},
            {"entityDistanceScaling", "0.75"}
    };

    @Override
    public void onPreLaunch() {
        try {
            Path dir = FabricLoader.getInstance().getGameDir();
            Path marker = dir.resolve(".movilboost_applied");
            if (Files.exists(marker)) return;

            Path file = dir.resolve("options.txt");
            List<String> lines = Files.exists(file) ? new ArrayList<>(Files.readAllLines(file)) : new ArrayList<>();
            for (String[] o : OPTS) {
                boolean found = false;
                for (int i = 0; i < lines.size(); i++) {
                    if (lines.get(i).startsWith(o[0] + ":")) {
                        lines.set(i, o[0] + ":" + o[1]);
                        found = true;
                        break;
                    }
                }
                if (!found) lines.add(o[0] + ":" + o[1]);
            }
            Files.write(file, lines);
            Files.writeString(marker, "ok");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
