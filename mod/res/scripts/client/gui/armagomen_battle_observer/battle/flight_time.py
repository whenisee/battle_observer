import Math
from gui.Scaleform.daapi.view.battle.shared.crosshair.container import CrosshairPanelContainer
from gui.shared.gui_items.Vehicle import VEHICLE_CLASS_NAME

from ..core.battle_cache import cache
from ..core.bo_constants import FLIGHT_TIME, GLOBAL
from ..core.config import cfg
from ..core.core import SafeDict
from ..meta.battle.flight_time_meta import FlyghtTimeMeta

VECTOR = Math.Vector3(GLOBAL.F_ZERO, GLOBAL.F_ZERO, GLOBAL.F_ZERO)
config = cfg.flight_time


class FlightTime(FlyghtTimeMeta):

    def __init__(self):
        super(FlightTime, self).__init__()
        self.wg_distance = CrosshairPanelContainer.setDistance
        self.template = config[FLIGHT_TIME.TEMPLATE]
        self.wgDistDisable = config[FLIGHT_TIME.WG_DIST_DISABLE]
        self.isSPG = False
        self.arenaVisitor = self.sessionProvider.arenaVisitor
        self.shared = self.sessionProvider.shared
        self.macrosDict = SafeDict({FLIGHT_TIME.M_FLIGHT_TIME: GLOBAL.ZERO, FLIGHT_TIME.M_DISTANCE: GLOBAL.ZERO})

    def _populate(self):
        super(FlightTime, self)._populate()
        self.as_startUpdateS(config)

    def checkSpgOnlyConfig(self):
        if config[FLIGHT_TIME.SPG_ONLY]:
            return self.isSPG
        return True

    def onEnterBattlePage(self):
        super(FlightTime, self).onEnterBattlePage()
        self.isSPG = VEHICLE_CLASS_NAME.SPG in cache.player.vehicleTypeDescriptor.type.tags
        if self.checkSpgOnlyConfig():
            if self.shared.crosshair:
                self.shared.crosshair.onGunMarkerStateChanged += self.__onGunMarkerStateChanged
            arena = self.arenaVisitor.getArenaSubscription()
            if arena:
                arena.onVehicleKilled += self.__onVehicleKilled
            if self.wgDistDisable:
                CrosshairPanelContainer.setDistance = lambda *args: None

    def onExitBattlePage(self):
        if self.checkSpgOnlyConfig():
            if self.shared.crosshair:
                self.shared.crosshair.onGunMarkerStateChanged -= self.__onGunMarkerStateChanged
            arena = self.arenaVisitor.getArenaSubscription()
            if arena:
                arena.onVehicleKilled -= self.__onVehicleKilled
            if self.wgDistDisable:
                CrosshairPanelContainer.setDistance = self.wg_distance
        super(FlightTime, self).onExitBattlePage()

    def __onVehicleKilled(self, targetID, attackerID, equipmentID, reason):
        if targetID == cache.player.playerVehicleID:
            self.as_flyghtTimeS(GLOBAL.EMPTY_LINE)

    def __onGunMarkerStateChanged(self, markerType, position, params, collision):
        shotPos, shotVec = cache.player.gunRotator.getCurShotPosition()
        flatDist = position.flatDistTo(shotPos)
        self.macrosDict[FLIGHT_TIME.M_FLIGHT_TIME] = flatDist / shotVec.flatDistTo(VECTOR)
        self.macrosDict[FLIGHT_TIME.M_DISTANCE] = flatDist
        self.as_flyghtTimeS(self.template % self.macrosDict)
