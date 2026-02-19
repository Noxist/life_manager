/**
 * ManageEntriesPage — view and delete today's water entries.
 *
 * Entries are shown in reverse chronological order (newest first).
 * Tapping the ✕ icon deletes the entry and re-syncs with HA.
 *
 * @see https://developer.huawei.com/consumer/en/doc/design-guides/spacing-parameters-0000002202912577
 */
import router from '@ohos.router';
import { Constants } from '../common/Constants';
import { StorageService } from '../service/StorageService';
import { HASyncService } from '../service/HASyncService';
import { ServerService } from '../service/ServerService';
import { WaterEntry, DayLog } from '../model/WaterModel';

@Entry
@Component
struct ManageEntriesPage {
  @State private entries: WaterEntry[] = [];
  @State private totalIntake: number = 0;
  @State private isLoading: boolean = true;

  aboutToAppear(): void {
    this.loadEntries();
  }

  private async loadEntries(): Promise<void> {
    const log: DayLog = await StorageService.getTodayLog();
    this.entries = log.entries.slice().reverse();
    this.totalIntake = log.totalIntake;
    this.isLoading = false;
  }

  private async deleteEntry(entryId: string): Promise<void> {
    const log: DayLog = await StorageService.deleteEntry(entryId);
    this.entries = log.entries.slice().reverse();
    this.totalIntake = log.totalIntake;
    HASyncService.syncToHA(log);
    // Trigger server sync after delete
    const serverOn: boolean = await StorageService.isServerEnabled();
    if (serverOn) {
      ServerService.reportStatus();
    }
  }

  private formatTime(timestamp: number): string {
    const d: Date = new Date(timestamp);
    const h: string = String(d.getHours()).padStart(2, '0');
    const m: string = String(d.getMinutes()).padStart(2, '0');
    return `${h}:${m}`;
  }

  build() {
    Column() {
      // ── Header ──
      Text('Entries')
        .fontSize(14)
        .fontWeight(FontWeight.Bold)
        .fontColor(Constants.COLOR_TEXT_PRIMARY)
        .margin({ top: 4 })

      Text(`Total: ${this.totalIntake} ml`)
        .fontSize(10)
        .fontColor(Constants.COLOR_TEXT_SECONDARY)
        .margin({ top: 2, bottom: 6 })

      if (this.isLoading) {
        Text('Loading...')
          .fontSize(12)
          .fontColor(Constants.COLOR_TEXT_SECONDARY)
      } else if (this.entries.length === 0) {
        Text('No entries today')
          .fontSize(11)
          .fontColor(Constants.COLOR_TEXT_SECONDARY)
      } else {
        // ── Scrollable entry list ──
        Scroll() {
          Column() {
            ForEach(this.entries, (entry: WaterEntry) => {
              Row() {
                Text(`${entry.amount} ml`)
                  .fontSize(12)
                  .fontWeight(FontWeight.Medium)
                  .fontColor(Constants.COLOR_TEXT_PRIMARY)
                  .layoutWeight(1)

                Text(this.formatTime(entry.timestamp))
                  .fontSize(10)
                  .fontColor(Constants.COLOR_TEXT_SECONDARY)
                  .margin({ right: 6 })

                Text('✕')
                  .fontSize(16)
                  .fontWeight(FontWeight.Bold)
                  .fontColor(Constants.COLOR_WARNING)
                  .width(36)
                  .height(36)
                  .textAlign(TextAlign.Center)
                  .borderRadius(18)
                  .backgroundColor(Constants.COLOR_PROGRESS_BG)
                  .onClick(() => { this.deleteEntry(entry.id); })
              }
              .width('100%')
              .height(44)
              .padding({ left: 10, right: 6 })
              .borderRadius(10)
              .backgroundColor(Constants.COLOR_SURFACE)
              .margin({ bottom: 6 })
            }, (entry: WaterEntry) => entry.id)
          }
          .width('100%')
        }
        .layoutWeight(1)
        .scrollBar(BarState.Off)
        .margin({ top: 4 })
      }

      // ── Back ──
      Text('← Back')
        .fontSize(11)
        .fontColor(Constants.COLOR_PRIMARY)
        .margin({ top: 8, bottom: 4 })
        .onClick(() => { router.back(); })
    }
    .width('100%')
    .height('100%')
    .padding({
      left: Constants.MARGIN_LEFT,
      right: Constants.MARGIN_RIGHT,
      top: Constants.PADDING_CONTENT_TOP,
      bottom: Constants.PADDING_CONTENT_BOTTOM
    })
    .backgroundColor(Constants.COLOR_BACKGROUND)
  }
}
