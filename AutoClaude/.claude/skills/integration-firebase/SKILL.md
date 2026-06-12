---
name: integration-firebase
description: 整合 Firebase 服務，包含 Auth、Firestore、Storage、Cloud Functions
user-invocable: true
disable-model-invocation: false
argument-hint: "<service: Firebase 服務 (auth/firestore/storage/functions/all)> [framework: 框架 (nextjs/react/vue)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration Firebase Skill

整合 Firebase 後端即服務 (BaaS)。

---

## 觸發方式

```bash
/integration-firebase auth           # Firebase Auth
/integration-firebase firestore      # Firestore 資料庫
/integration-firebase all nextjs     # 全部服務 + Next.js
```

---

## 執行流程

### 階段 1: Firebase 設定確認 🔴

**確認項目**:
- [ ] Firebase 專案已建立
- [ ] 需要的服務已啟用
- [ ] 環境變數已配置
- [ ] 安全規則已規劃

**環境變數**:
```env
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

🔴 **確認點**: 確認 Firebase 配置

---

### 階段 2: Firebase 初始化

```typescript
// src/lib/firebase/config.ts
import { initializeApp, getApps, FirebaseApp } from 'firebase/app';
import { getAuth, Auth } from 'firebase/auth';
import { getFirestore, Firestore } from 'firebase/firestore';
import { getStorage, FirebaseStorage } from 'firebase/storage';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

let app: FirebaseApp;
let auth: Auth;
let db: Firestore;
let storage: FirebaseStorage;

if (typeof window !== 'undefined') {
  app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
  auth = getAuth(app);
  db = getFirestore(app);
  storage = getStorage(app);
}

export { app, auth, db, storage };
```

---

### 階段 3: Firebase Authentication

```typescript
// src/lib/firebase/auth.ts
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  signInWithPopup,
  GoogleAuthProvider,
  onAuthStateChanged,
  User,
  sendPasswordResetEmail,
  updateProfile,
} from 'firebase/auth';
import { auth } from './config';

const googleProvider = new GoogleAuthProvider();

export const firebaseAuth = {
  // 郵件登入
  async signIn(email: string, password: string) {
    const result = await signInWithEmailAndPassword(auth, email, password);
    return result.user;
  },

  // 郵件註冊
  async signUp(email: string, password: string, displayName?: string) {
    const result = await createUserWithEmailAndPassword(auth, email, password);
    if (displayName) {
      await updateProfile(result.user, { displayName });
    }
    return result.user;
  },

  // Google 登入
  async signInWithGoogle() {
    const result = await signInWithPopup(auth, googleProvider);
    return result.user;
  },

  // 登出
  async signOut() {
    await firebaseSignOut(auth);
  },

  // 重設密碼
  async resetPassword(email: string) {
    await sendPasswordResetEmail(auth, email);
  },

  // 監聽登入狀態
  onAuthStateChange(callback: (user: User | null) => void) {
    return onAuthStateChanged(auth, callback);
  },

  // 取得當前使用者
  getCurrentUser() {
    return auth.currentUser;
  },
};
```

```typescript
// src/hooks/useAuth.ts
'use client';

import { useState, useEffect } from 'react';
import { User } from 'firebase/auth';
import { firebaseAuth } from '@/lib/firebase/auth';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = firebaseAuth.onAuthStateChange((user) => {
      setUser(user);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  return { user, loading };
}
```

---

### 階段 4: Firestore 資料庫

```typescript
// src/lib/firebase/firestore.ts
import {
  collection,
  doc,
  getDoc,
  getDocs,
  addDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  onSnapshot,
  Timestamp,
  DocumentData,
  QueryConstraint,
} from 'firebase/firestore';
import { db } from './config';

export function createFirestoreService<T extends DocumentData>(collectionName: string) {
  const collectionRef = collection(db, collectionName);

  return {
    // 取得單一文檔
    async getById(id: string): Promise<T | null> {
      const docRef = doc(db, collectionName, id);
      const docSnap = await getDoc(docRef);
      return docSnap.exists() ? ({ id: docSnap.id, ...docSnap.data() } as T) : null;
    },

    // 取得所有文檔
    async getAll(constraints: QueryConstraint[] = []): Promise<T[]> {
      const q = query(collectionRef, ...constraints);
      const snapshot = await getDocs(q);
      return snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() } as T));
    },

    // 新增文檔
    async create(data: Omit<T, 'id'>): Promise<string> {
      const docRef = await addDoc(collectionRef, {
        ...data,
        createdAt: Timestamp.now(),
        updatedAt: Timestamp.now(),
      });
      return docRef.id;
    },

    // 更新文檔
    async update(id: string, data: Partial<T>): Promise<void> {
      const docRef = doc(db, collectionName, id);
      await updateDoc(docRef, {
        ...data,
        updatedAt: Timestamp.now(),
      });
    },

    // 刪除文檔
    async delete(id: string): Promise<void> {
      const docRef = doc(db, collectionName, id);
      await deleteDoc(docRef);
    },

    // 即時監聽
    subscribe(callback: (data: T[]) => void, constraints: QueryConstraint[] = []) {
      const q = query(collectionRef, ...constraints);
      return onSnapshot(q, (snapshot) => {
        const data = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() } as T));
        callback(data);
      });
    },
  };
}

// 使用範例
export interface UserProfile {
  id: string;
  displayName: string;
  email: string;
  photoURL?: string;
  createdAt: Timestamp;
}

export const usersService = createFirestoreService<UserProfile>('users');
```

---

### 階段 5: Firebase Storage

```typescript
// src/lib/firebase/storage.ts
import {
  ref,
  uploadBytes,
  uploadBytesResumable,
  getDownloadURL,
  deleteObject,
  listAll,
} from 'firebase/storage';
import { storage } from './config';

export const firebaseStorage = {
  // 上傳檔案
  async upload(path: string, file: File): Promise<string> {
    const storageRef = ref(storage, path);
    await uploadBytes(storageRef, file);
    return getDownloadURL(storageRef);
  },

  // 上傳並追蹤進度
  uploadWithProgress(
    path: string,
    file: File,
    onProgress: (progress: number) => void
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const storageRef = ref(storage, path);
      const uploadTask = uploadBytesResumable(storageRef, file);

      uploadTask.on(
        'state_changed',
        (snapshot) => {
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
          onProgress(progress);
        },
        (error) => reject(error),
        async () => {
          const url = await getDownloadURL(uploadTask.snapshot.ref);
          resolve(url);
        }
      );
    });
  },

  // 取得下載 URL
  async getUrl(path: string): Promise<string> {
    const storageRef = ref(storage, path);
    return getDownloadURL(storageRef);
  },

  // 刪除檔案
  async delete(path: string): Promise<void> {
    const storageRef = ref(storage, path);
    await deleteObject(storageRef);
  },

  // 列出檔案
  async list(path: string) {
    const storageRef = ref(storage, path);
    const result = await listAll(storageRef);
    return result.items;
  },
};
```

---

### 階段 6: 驗證 🔴

**驗證清單**:
- [ ] Authentication 登入/註冊正常
- [ ] Firestore CRUD 運作
- [ ] Storage 上傳/下載正常
- [ ] 安全規則正確配置
- [ ] 錯誤處理正確

🔴 **確認點**: 確認 Firebase 服務整合正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Firebase 配置 | `src/lib/firebase/config.ts` |
| Auth 服務 | `src/lib/firebase/auth.ts` |
| Firestore 服務 | `src/lib/firebase/firestore.ts` |
| Storage 服務 | `src/lib/firebase/storage.ts` |

---

## 相關 Skill

- `/integration-oauth` - OAuth 認證
- `/integration-api-client` - API 客戶端

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
