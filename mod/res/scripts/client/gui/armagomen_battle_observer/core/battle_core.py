from CurrentVehicle import g_currentVehicle
from PlayerEvents import g_playerEvents
from constants import ARENA_GUI_TYPE
from gui.Scaleform.daapi.view.battle.shared.postmortem_panel import PostmortemPanel
from gui.shared.personality import ServicesLocator
from helpers import dependency
from skeletons.gui.battle_session import IBattleSessionProvider

from .battle_cache import cache, g_health
from .bo_constants import VEHICLE, MAIN, GLOBAL, POSTMORTEM, MAIN_GUN
from .bw_utils import getPlayer, setMaxFrameRate
from .config import cfg
from .core import overrideMethod
from .events import g_events


def getArenaVisitor():
    return dependency.instance(IBattleSessionProvider).arenaVisitor


class _BattleCore(object):

    def __init__(self):
        self.load_health_module = False
        self.callbackTime = 0.01
        g_playerEvents.onArenaCreated += self.onArenaCreated
        g_playerEvents.onAvatarReady += self.onEnterBattlePage
        g_playerEvents.onAvatarBecomeNonPlayer += self.onExitBattlePage
        g_events.onSettingsChanged += self.onSettingsChanged

    @staticmethod
    @overrideMethod(PostmortemPanel, "getDeathInfo")
    def getDeathInfo(base, *args, **kwargs):
        if not (cfg.postmortem_panel[GLOBAL.ENABLED] and cfg.postmortem_panel[POSTMORTEM.HIDE_KILLER]):
            return base(*args, **kwargs)

    @staticmethod
    def onSettingsChanged(config, blockID):
        if blockID == MAIN.NAME and config[MAIN.ENABLE_FPS_LIMITER]:
            setMaxFrameRate(config[MAIN.MAX_FRAME_RATE])

    @staticmethod
    def onArenaCreated():
        intCD = getattr(g_currentVehicle.item, "intCD", None)
        if intCD:
            avg = ServicesLocator.itemsCache.items.getVehicleDossier(intCD).getRandomStats().getAvgDamage()
            if avg is not None:
                cache.tankAvgDamage = float(avg)

    @staticmethod
    def isTeamHealthEnabled():
        return cfg.hp_bars[GLOBAL.ENABLED] or \
               cfg.main_gun[GLOBAL.ENABLED] and cfg.main_gun[MAIN_GUN.DYNAMIC] or \
               cfg.players_damages[GLOBAL.ENABLED] or \
               cfg.players_bars[GLOBAL.ENABLED]

    @staticmethod
    def isAllowedBattleType(arenaVisitor=None):
        enabled = False
        if arenaVisitor is None:
            arenaVisitor = getArenaVisitor()
        if arenaVisitor is not None:
            enabled = arenaVisitor.gui.isRandomBattle() or \
                      arenaVisitor.gui.isTrainingBattle() or \
                      arenaVisitor.gui.isRankedBattle() or \
                      arenaVisitor.getArenaGuiType() in (ARENA_GUI_TYPE.UNKNOWN,
                                                         ARENA_GUI_TYPE.FORT_BATTLE_2,
                                                         ARENA_GUI_TYPE.SORTIE_2)
        return enabled, arenaVisitor

    def onEnterBattlePage(self):
        cache.player = getPlayer()
        g_events.onEnterBattlePage()
        enabled, arenaVisitor = self.isAllowedBattleType()
        if enabled and arenaVisitor is not None:
            arena = arenaVisitor.getArenaSubscription()
            if arena is not None:
                arena.onVehicleKilled += self.onVehicleKilled
            self.load_health_module = self.isTeamHealthEnabled()
            if self.load_health_module:
                g_events.onHealthChanged += self.healthChanged
                if cache.player and hasattr(cache.player, "onVehicleEnterWorld"):
                    cache.player.onVehicleEnterWorld += self.onEnterWorld
                if arena is not None:
                    arena.onVehicleAdded += self.onVehicleAddUpdate
                    arena.onVehicleUpdated += self.onVehicleAddUpdate

    def onExitBattlePage(self):
        g_events.onExitBattlePage()
        enabled, arenaVisitor = self.isAllowedBattleType()
        if enabled and arenaVisitor is not None:
            arena = arenaVisitor.getArenaSubscription()
            if arena is not None:
                arena.onVehicleKilled -= self.onVehicleKilled
            if self.load_health_module:
                g_events.onHealthChanged -= self.healthChanged
                if cache.player and hasattr(cache.player, "onVehicleEnterWorld"):
                    cache.player.onVehicleEnterWorld -= self.onEnterWorld
                if arena is not None:
                    arena.onVehicleAdded -= self.onVehicleAddUpdate
                    arena.onVehicleUpdated -= self.onVehicleAddUpdate
        self.load_health_module = False

    @staticmethod
    def healthChanged(vehicle, newHealth, attackerID, aRID):
        team = vehicle.publicInfo.team
        g_health.setNewHealth(team, vehicle.id, newHealth, attackerID=attackerID)

    def onVehicleKilled(self, targetID, attackerID, *args):
        if self.load_health_module:
            team = g_health.getVehicle(targetID)[VEHICLE.TEAM]
            g_health.setNewHealth(team, targetID, GLOBAL.ZERO, attackerID=attackerID)
        if cache.player.playerVehicleID == targetID:
            g_events.onPlayerVehicleDeath(attackerID)
        elif cache.player.playerVehicleID == attackerID:
            g_events.onPlayerKilledEnemy(targetID)

    @staticmethod
    def onEnterWorld(vehicle):
        if vehicle.isAlive():
            g_health.setNewHealth(vehicle.publicInfo.team, vehicle.id, vehicle.health)

    def onVehicleAddUpdate(self, vehID):
        vInfoVO = cache.arenaDP.getVehicleInfo(vehID)
        if vInfoVO:
            vehicleType = vInfoVO.vehicleType
            if vehicleType and vehicleType.maxHealth and vehicleType.classTag:
                g_health.addVehicle(vInfoVO)
                g_events.onVehicleAddUpdate(vehID, vehicleType)


b_core = _BattleCore()
