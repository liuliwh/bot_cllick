/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* kb.mozillazine.org/App.update.channel
安装文件中默认值为release.这里改为default.
Set to default, means No updates are offered.
如果仅只设置policies文件disableupdate的话，而不修改channel的话，
依然会有对话框，需要辅以配置
app.update.interval， app.update.interval，app.update.promptWaitTime
等值，故选择通过chanel来控制*/
pref("app.update.channel", "default");
